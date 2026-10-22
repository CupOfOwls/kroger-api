import base64
import logging
import os
import ssl
import time
from typing import Dict, Iterator, Optional, Any, Tuple, Union
from urllib.parse import quote, urlencode, urljoin

import requests
import urllib3

try:
    from urllib3.util.ssl_match_hostname import CertificateError as _HostnameMismatchError
except ImportError:  # urllib3 before 1.26.5 keeps it in urllib3.packages
    _HostnameMismatchError = ssl.CertificateError

from kroger_api import validation
from kroger_api.errors import (
    KrogerAPIError,
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    ConfigurationError,
    InvalidResponseError,
    NotAuthenticatedError,
    error_from_response,
)

from kroger_api.token_storage import USER_TOKEN_FILE, load_token, save_token, token_file_lock
from kroger_api.utils.env import load_env_file

logger = logging.getLogger(__name__)

# Seconds to wait for the Kroger API before raising APITimeoutError.
DEFAULT_TIMEOUT = 30

# Treat a token as expired this many seconds early, so it does not expire
# between the check and the request.
EXPIRY_MARGIN_SECONDS = 60

# Failures that happen while the connection is being set up, so before any
# part of the request is sent: DNS failures and refused connections
# (NewConnectionError), also to a proxy, and a certificate the client does
# not accept, which fails the TLS handshake. ProxyError alone is not one of
# them: urllib3 1.26 and 2 both raise it for a connection through a proxy
# that is lost after the request was sent (urllib3 2 resets
# has_connected_to_proxy when http.client closes the failed connection).
_SETUP_FAILURES = (urllib3.exceptions.NewConnectionError, ssl.SSLCertVerificationError, _HostnameMismatchError)


def _causes(error: BaseException) -> Iterator[BaseException]:
    """error and the exceptions it wraps, through args, reason, and __cause__"""
    pending, seen = [error], set()
    while pending and len(seen) < 20:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        wrapped = [*current.args, getattr(current, "reason", None), current.__cause__]
        pending.extend(e for e in wrapped if isinstance(e, BaseException))


class KrogerClient:
    """
    Base client for interacting with the Kroger API
    """
    BASE_URL = "https://api.kroger.com"
     
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None,
                 timeout: Optional[float] = DEFAULT_TIMEOUT):
        """
        Initialize the Kroger API client
        
        Args:
            client_id: Your Kroger API client ID
            client_secret: Your Kroger API client secret
            redirect_uri: The redirect URI registered with your Kroger API application
            timeout: Seconds to wait for each API response before raising
                APITimeoutError (None waits indefinitely)

        Raises:
            ConfigurationError: If the client ID or secret is missing
        """
        # A .env file in the working directory supplements the environment
        load_env_file()
        self.client_id = client_id or os.getenv("KROGER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("KROGER_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("KROGER_REDIRECT_URI")
        self.timeout = timeout
        
        missing = [name for name, value in (("KROGER_CLIENT_ID", self.client_id),
                                            ("KROGER_CLIENT_SECRET", self.client_secret)) if not value]
        if missing:
            raise ConfigurationError(
                f"Missing Kroger API credentials: {', '.join(missing)}. Pass client_id and client_secret, "
                "or set the environment variables (a .env file in the working directory also works)."
            )
        
        self.token_info = None
        self.token_file = None
        # The last client-credentials token and its scope, so that a rejected
        # app token can be replaced without the caller's help. Only that exact
        # token is replaced: a user token put in token_info is never swapped
        # for an app token.
        self._client_credentials_scope = None
        self._client_credentials_access_token = None
    
    def get_authorization_url(self, scope: str, state: Optional[str] = None, banner: Optional[str] = None, code_challenge: Optional[str] = None, code_challenge_method: Optional[str] = None) -> str:
        """
        Get the URL to redirect the user to for authorization
        
        Args:
            scope: The level of access your application is requesting
            state: A random string to verify that the response belongs to the initiated request
            banner: Sets the chain specific branding displayed on the authorization consent screen
            code_challenge: PKCE code challenge for enhanced security (recommended)
            code_challenge_method: Method used to generate the code challenge (S256 is recommended)
            
        Returns:
            The authorization URL

        Raises:
            ConfigurationError: If no redirect URI is configured
        """
        if not self.redirect_uri:
            raise ConfigurationError(
                "Missing redirect_uri for the authorization code flow. Pass redirect_uri or set "
                "KROGER_REDIRECT_URI to the redirect URI registered for your app."
            )
        validation.check_non_empty("scope", scope)
        params = {
            'scope': scope,
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code'
        }
        
        if state:
            params['state'] = state
        
        if banner:
            params['banner'] = banner
            
        # Add PKCE parameters if provided
        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = code_challenge_method or 'S256'
        
        url = urljoin(self.BASE_URL, "/v1/connect/oauth2/authorize")
        # Percent-encode every value: the scope has spaces, and the redirect
        # URI and state can hold characters such as & and =
        return url + "?" + urlencode(params, quote_via=quote)
    
    def get_token_with_client_credentials(self, scope: str) -> Dict[str, Any]:
        """
        Get an access token using client credentials
        
        Args:
            scope: The level of access your application is requesting
            
        Returns:
            The token information

        Raises:
            InvalidParameterError: If scope is empty
            AuthenticationError: If Kroger rejects the client ID and secret
            BadRequestError: If the scope is not valid for this app
        """
        validation.check_non_empty("scope", scope)
        # Set the token file for this scope (resolved to a writable
        # directory by token_storage.get_token_file_path)
        self.token_file = f".kroger_token_client_{scope.replace(':', '_')}.json"
        self._client_credentials_scope = scope
        
        # Reuse a saved token while it is unexpired
        token_info = load_token(self.token_file)
        if token_info and token_info.get("access_token") and not self.is_token_expired(token_info):
            self.token_info = token_info
        else:
            if token_info:
                logger.info("Saved client-credentials token has expired, requesting a new one")
            token_info = self._get_token(grant_type="client_credentials", scope=scope)
            save_token(token_info, self.token_file)

        self._client_credentials_access_token = token_info["access_token"]
        return token_info
    
    def get_token_with_authorization_code(self, code: str, code_verifier: Optional[str] = None,
                                          token_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an access token using an authorization code
        
        Args:
            code: The authorization code received from the redirect
            code_verifier: PKCE code verifier used during authorization (if PKCE was used)
            token_file: The file to save the user token to (default USER_TOKEN_FILE).
                Later refreshes save to the same file.
            
        Returns:
            The token information

        Raises:
            ConfigurationError: If no redirect URI is configured
            BadRequestError: If the code is invalid, expired, or already used,
                or the redirect URI or code verifier does not match
        """
        if not self.redirect_uri:
            raise ConfigurationError(
                "Missing redirect_uri for the authorization code flow. Pass redirect_uri or set "
                "KROGER_REDIRECT_URI to the redirect URI registered for your app."
            )
        validation.check_non_empty("code", code)

        # A user token never goes to this client's client-credentials file
        self.token_file = token_file or USER_TOKEN_FILE
        
        # Prepare parameters for token request
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        # Add code_verifier if provided (for PKCE)
        if code_verifier:
            params['code_verifier'] = code_verifier
        
        token_info = self._get_token(**params)
        
        # Save it with the file locked, so a refresh of the previous sign-in
        # that is in progress cannot overwrite it afterwards
        with token_file_lock(self.token_file):
            save_token(token_info, self.token_file)
        
        return token_info
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token

        The new token is saved to the client's token file (USER_TOKEN_FILE
        if it has none), and the file's lock is held while the token is
        refreshed and saved. This method always sends the given refresh
        token; AuthorizationAPI.refresh_token_if_needed instead first checks
        whether another process has refreshed the saved token already.
        
        Args:
            refresh_token: The refresh token received from a previous token request
            
        Returns:
            The token information

        Raises:
            BadRequestError: If the refresh token is invalid or expired
        """
        token_file = self.token_file or USER_TOKEN_FILE
        with token_file_lock(token_file):
            return self._refresh(refresh_token, token_file)

    def _refresh(self, refresh_token: str, token_file: str) -> Dict[str, Any]:
        """Refresh the token and save it to token_file; the caller holds the file's lock"""
        try:
            token_info = self._get_token(
                grant_type="refresh_token",
                refresh_token=refresh_token
            )
        except BadRequestError:
            logger.warning("Kroger rejected the refresh token; the user has to sign in again")
            raise
            
        # RFC 6749 section 6: when the server issues no new refresh token,
        # the old one stays valid. Keep it so the next expiry can refresh too.
        if "refresh_token" not in token_info:
            token_info["refresh_token"] = refresh_token
            
        save_token(token_info, token_file)
        return token_info

    def _renew_user_token(self, token_file: str, replaced: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Replace a user token that has expired or was rejected, with the token file locked

        Threads and processes that share token_file renew its token one at a
        time. One that waited for the lock may find that another has renewed
        the token meanwhile (see _renewed_since); it then uses the saved
        token. Otherwise the refresh token in the file is tried first, then
        the replaced token's if it differs. The file holds the newest refresh
        token. Sending one that was already used first would risk Kroger
        revoking the newer one too, as RFC 9700 section 4.14.2 recommends.
        If Kroger rejects them all, the file is read once more, in case a
        process that does not take the lock (an older version, or one that
        gave up waiting for it) saved a renewed token meanwhile.

        Args:
            token_file: The file the token is read from and saved to
            replaced: The token information that expired or was rejected

        Returns:
            The new token information, now in token_info, or None if there
            is no refresh token to try

        Raises:
            BadRequestError: If Kroger rejected every refresh token (the last rejection)
            KrogerAPIError: If the token request fails for another reason
        """
        with token_file_lock(token_file):
            saved = load_token(token_file)
            saved = saved if isinstance(saved, dict) else {}
            if self._renewed_since(saved, replaced):
                logger.info("The saved token was renewed by another thread or process; using it")
                self.token_info = saved
                return saved

            rejection = None
            for candidate in dict.fromkeys(t for t in (saved.get("refresh_token"), replaced.get("refresh_token")) if t):
                logger.info("Refreshing the access token")
                try:
                    return self._refresh(candidate, token_file)
                except BadRequestError as e:
                    rejection = e
            if rejection is not None:
                latest = load_token(token_file)
                if isinstance(latest, dict) and self._renewed_since(latest, replaced):
                    logger.info("The saved token was renewed by another process; using it")
                    self.token_info = latest
                    return latest
                raise rejection
            return None

    @classmethod
    def _renewed_since(cls, saved: Dict[str, Any], replaced: Dict[str, Any]) -> bool:
        """True if saved is a user token, unexpired, and issued after replaced

        A user token has a refresh token. All Kroger tokens last equally
        long, so the one that expires later was issued later. A saved token
        that is older than the replaced one, for example because saving the
        replaced one failed, is not used. Neither is one whose age cannot be
        compared.
        """
        if not saved.get("access_token") or not saved.get("refresh_token"):
            return False
        if saved["access_token"] == replaced.get("access_token") or cls.is_token_expired(saved):
            return False
        try:
            return float(saved["expires_at"]) > float(replaced["expires_at"])
        except (KeyError, TypeError, ValueError):
            return False
    
    def test_token(self, token_info: Dict[str, Any]) -> bool:
        """
        Check whether a token can be used now, refreshing it if it has expired

        The check is local: it compares the token's expiry time with the
        clock, so it costs no API call. Earlier versions called
        /v1/connect/oauth2/profile, which does not exist, so every token
        tested invalid. A token revoked before it expires still tests valid;
        the next API call then gets a 401, which _make_request handles by
        refreshing the token and retrying once.
        
        Args:
            token_info: The token information
            
        Returns:
            True if the token is unexpired, or expired and refreshed successfully.
            False if it is expired and cannot be refreshed.
        """
        if not token_info or not token_info.get("access_token"):
            return False
                
        if not self.is_token_expired(token_info):
            return True
                
        refresh_token = token_info.get("refresh_token")
        if not refresh_token:
            return False
                
        try:
            logger.info("Access token has expired, refreshing it")
            if self.token_file:
                return self._renew_user_token(self.token_file, token_info) is not None
            self.refresh_token(refresh_token)
            return True
        except KrogerAPIError as e:
            logger.warning("Failed to refresh token: %s", e)
            return False
                
    @staticmethod
    def is_token_expired(token_info: Dict[str, Any]) -> bool:
        """True if the token's expires_at time (less a margin) has passed.
                
        A token without expires_at, such as one built by hand, counts as
        unexpired; a 401 on use triggers the refresh instead.
        """
        expires_at = token_info.get("expires_at")
        if expires_at is None:
            return False
        try:
            return time.time() >= float(expires_at) - EXPIRY_MARGIN_SECONDS
        except (TypeError, ValueError):
            return False
    
    def _get_token(self, grant_type: str, **kwargs) -> Dict[str, Any]:
        """
        Get an access token
        
        Args:
            grant_type: The OAuth2 grant type
            **kwargs: Additional parameters for the token request
            
        Returns:
            The token information, with an added expires_at (Unix time)
        """
        url = urljoin(self.BASE_URL, "/v1/connect/oauth2/token")
        
        auth_header = self._get_basic_auth_header()
        
        data = {
            'grant_type': grant_type,
            **kwargs
        }
        
        response = self._send('POST', url, headers=auth_header, data=data)
        if not response.ok:
            raise error_from_response(response)
        
        token_info = self._parse_json(response)
        if not isinstance(token_info, dict) or not token_info.get("access_token"):
            raise InvalidResponseError(response)
        if token_info.get("expires_in") is not None:
            token_info["expires_at"] = time.time() + float(token_info["expires_in"])

        self.token_info = token_info
        return self.token_info
    
    def _get_basic_auth_header(self) -> Dict[str, str]:
        """
        Get the HTTP basic authentication header using client ID and secret
        
        Returns:
            The HTTP basic authentication header
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_credentials}'
        }
    
    def _get_auth_header(self, token_info: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Get the authorization header using the current token

        Args:
            token_info: The token to use (default token_info)
        
        Returns:
            The authorization header with the access token
            
        Raises:
            NotAuthenticatedError: If there is no token information available
        """
        token_info = token_info if token_info is not None else self.token_info
        if not token_info or 'access_token' not in token_info:
            raise NotAuthenticatedError(
                "No access token available. Get one first with get_token_with_client_credentials(), "
                "get_token_with_authorization_code(), or kroger_api.auth.authenticate_user()."
            )
        
        return {
            'Authorization': f"Bearer {token_info['access_token']}",
            'Accept': 'application/json'
        }

    def _send(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Send one HTTP request, converting network failures to kroger-api errors

        Raises:
            APITimeoutError: If no response arrives within self.timeout
            APIConnectionError: If the request fails without an HTTP response
        """
        try:
            return requests.request(method=method, url=url, timeout=self.timeout, **kwargs)
        except requests.exceptions.Timeout as e:
            sent = False if isinstance(e, requests.exceptions.ConnectTimeout) else None
            raise APITimeoutError(method, self._url_for(e, url), self.timeout, str(e), request=e.request,
                                  request_sent=sent) from e
        except requests.exceptions.RequestException as e:
            raise APIConnectionError(method, self._url_for(e, url), str(e), request=e.request,
                                     request_sent=self._request_sent(e)) from e

    @staticmethod
    def _request_sent(error: requests.exceptions.RequestException) -> Optional[bool]:
        """False if the request certainly never reached the server, else None (unknown)

        DNS failures, refused connections, and rejected certificates fail
        before anything is sent. Other TLS and proxy errors are not certain:
        urllib3 reports a TLS error while it reads the response the same way
        as one in the handshake, and a connection through a proxy lost after
        sending the same way as a proxy it could not use.
        """
        if any(isinstance(cause, _SETUP_FAILURES) for cause in _causes(error)):
            return False
        return None

    @staticmethod
    def _url_for(error: requests.exceptions.RequestException, fallback: str) -> str:
        request = getattr(error, "request", None)
        return getattr(request, "url", None) or fallback

    @staticmethod
    def _parse_json(response: requests.Response) -> Union[Dict[str, Any], None]:
        """The JSON body of a 2xx response, or None if it has no body."""
        # Some endpoints return 204 No Content, and HEAD responses have no body
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            raise InvalidResponseError(response) from None

    def _recover_from_unauthorized(self, rejected: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Replace a rejected access token, once

        The Kroger API answers an expired or revoked token with 401, a
        'WWW-Authenticate: Bearer ... error="invalid_token"' header, and a
        body of only {"message": "Unauthorized"}.

        If another thread has replaced token_info since the request was
        sent, the request is retried with that token. A client-credentials
        token is replaced with a new one for the same
        scope. A user token is renewed with token_file locked (see
        _renew_user_token): if another thread or process has renewed it
        already, the saved token is used; otherwise the refresh token in
        token_file is tried first, then the one in memory if it differs.
        Without a token_file, the refresh token in memory is used. Any other
        token is not replaced.

        Args:
            rejected: The token information the request was sent with

        Returns:
            (True, None) if a new token is in place, or (False, reason) if
            there is no way to get one or Kroger rejected the refresh token

        Raises:
            KrogerAPIError: If the token request fails for another reason,
                such as a network error or rejected client credentials. Its
                message describes the real problem better than the 401 does.
        """
        current = self.token_info or {}
        rejected_access_token = rejected.get("access_token")
        if current.get("access_token") and current["access_token"] != rejected_access_token:
            return True, None

        if self._client_credentials_scope and rejected_access_token == self._client_credentials_access_token:
            logger.info("Client-credentials token was rejected, requesting a new one")
            new_token = self._get_token(grant_type="client_credentials", scope=self._client_credentials_scope)
            self._client_credentials_access_token = new_token["access_token"]
            if self.token_file:
                save_token(new_token, self.token_file)
            return True, None

        refresh_token = rejected.get("refresh_token")
        logger.info("Access token was rejected, getting a new one")
        try:
            if self.token_file:
                renewed = self._renew_user_token(self.token_file, rejected)
            else:
                renewed = self.refresh_token(refresh_token) if refresh_token else None
        except BadRequestError as rejection:
            return False, f"Getting a new token failed: {rejection.message.splitlines()[0]}"
        if renewed is None:
            return False, "There is no refresh token, and the token is not a client-credentials token, so there is no way to get a new one."
        return True, None
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None,
                    headers: Optional[Dict] = None, read_body: bool = True) -> Union[Dict[str, Any], None]:
        """
        Make a request to the Kroger API
        
        Args:
            method: The HTTP method (GET, POST, PUT, etc.)
            endpoint: The API endpoint
            params: Query parameters
            data: Request body data
            headers: Additional HTTP headers
            read_body: False for a request whose response body is not used;
                any 2xx response then returns None
            
        Returns:
            The JSON response or None if response has no content

        Raises:
            APIStatusError: A subclass matching the status (BadRequestError,
                AuthenticationError, NotFoundError, ...) for any non-2xx response
            APIConnectionError: If the request fails without an HTTP response
            APITimeoutError: If no response arrives within the timeout
            InvalidResponseError: If a 2xx response is not valid JSON
            NotAuthenticatedError: If the client has no access token
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        def send() -> Tuple[Dict[str, Any], requests.Response]:
            # Another thread can replace token_info at any time, so keep the
            # token this request is sent with
            token_info = self.token_info
            # Combine default authorization headers with any additional headers
            request_headers = self._get_auth_header(token_info)
            if headers:
                request_headers.update(headers)
            # Use json parameter to automatically set Content-Type
            return token_info, self._send(method, url, params=params, json=data, headers=request_headers)
        
        sent_token, response = send()
            
        note = None
        if response.status_code == 401:
            recovered, note = self._recover_from_unauthorized(sent_token or {})
            if recovered:
                _, response = send()
                if response.status_code == 401:
                    note = "The request was retried once with a new token and was rejected again."
            
        if not response.ok:
            raise error_from_response(response, note=note)
        if not read_body:
            return None
                
        return self._parse_json(response)
