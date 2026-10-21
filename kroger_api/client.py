import sys
import os
import time
import base64
import requests
from typing import Dict, Optional, Any, Tuple, Union
from urllib.parse import urljoin
from dotenv import load_dotenv

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

# Import the token storage module
try:
    from kroger_api.token_storage import save_token, load_token, get_refresh_token
except ImportError:
    # For backwards compatibility
    save_token = lambda token_info, token_file=None: None
    load_token = lambda token_file=None: None
    get_refresh_token = lambda token_file=None: None

load_dotenv()

# Seconds to wait for the Kroger API before raising APITimeoutError.
DEFAULT_TIMEOUT = 30

# Treat a token as expired this many seconds early, so it does not expire
# between the check and the request.
EXPIRY_MARGIN_SECONDS = 60


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
        # Scope of the last client-credentials token, so an expired one can
        # be replaced without the caller's help.
        self._client_credentials_scope = None
    
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
        
        auth_path = "/v1/connect/oauth2/authorize"
        url = urljoin(self.BASE_URL, auth_path)
        
        # Build URL manually
        url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        return url
    
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
        if token_info:
            if self.test_token(token_info):
                self.token_info = token_info
                return token_info
            print("Saved client-credentials token has expired, requesting a new one", file=sys.stderr)
            
        token_info = self._get_token(grant_type="client_credentials", scope=scope)
        
        # Save the token for future use
        save_token(token_info, self.token_file)
        
        return token_info
    
    def get_token_with_authorization_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an access token using an authorization code
        
        Args:
            code: The authorization code received from the redirect
            code_verifier: PKCE code verifier used during authorization (if PKCE was used)
            
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

        # Set the token file for user tokens
        self.token_file = f".kroger_token_user.json"
        # A rejected user token must never be replaced by an app-only token
        self._client_credentials_scope = None
        
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
        
        # Save the token for future use
        save_token(token_info, self.token_file)
        
        return token_info
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token received from a previous token request
            
        Returns:
            The token information

        Raises:
            BadRequestError: If the refresh token is invalid or expired
        """
        try:
            token_info = self._get_token(
                grant_type="refresh_token",
                refresh_token=refresh_token
            )
        except BadRequestError:
            print("Invalid refresh token. Please re-authenticate.", file=sys.stderr)
            raise
            
        # RFC 6749 section 6: when the server issues no new refresh token,
        # the old one stays valid. Keep it so the next expiry can refresh too.
        if "refresh_token" not in token_info:
            token_info["refresh_token"] = refresh_token
            
        # Save the refreshed token
        if self.token_file:
            save_token(token_info, self.token_file)
        else:
            save_token(token_info, f".kroger_token_user.json")

        return token_info
    
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
            print("Access token has expired, refreshing it", file=sys.stderr)
            self.token_info = self.refresh_token(refresh_token)
            return True
        except KrogerAPIError as e:
            print(f"Failed to refresh token: {e}", file=sys.stderr)
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
    
    def _get_auth_header(self) -> Dict[str, str]:
        """
        Get the authorization header using the current token
        
        Returns:
            The authorization header with the access token
            
        Raises:
            NotAuthenticatedError: If there is no token information available
        """
        if not self.token_info or 'access_token' not in self.token_info:
            raise NotAuthenticatedError(
                "No access token available. Get one first with get_token_with_client_credentials(), "
                "get_token_with_authorization_code(), or kroger_api.auth.authenticate_user()."
            )
        
        return {
            'Authorization': f"Bearer {self.token_info['access_token']}",
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
            raise APITimeoutError(method, self._url_for(e, url), self.timeout, str(e), request=e.request) from e
        except requests.exceptions.RequestException as e:
            raise APIConnectionError(method, self._url_for(e, url), str(e), request=e.request) from e

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

    def _recover_from_unauthorized(self) -> Tuple[bool, Optional[str]]:
        """
        Replace a rejected access token, once

        The Kroger API answers an expired or revoked token with 401, a
        'WWW-Authenticate: Bearer ... error="invalid_token"' header, and a
        body of only {"message": "Unauthorized"}.

        Returns:
            (True, None) if a new token is in place, else (False, reason)
        """
        refresh_token = (self.token_info or {}).get("refresh_token")
        if not refresh_token and self.token_file:
            refresh_token = get_refresh_token(self.token_file)
        try:
            if refresh_token:
                print("Access token was rejected, refreshing it", file=sys.stderr)
                self.refresh_token(refresh_token)
                return True, None
            if self._client_credentials_scope:
                print("Client-credentials token was rejected, requesting a new one", file=sys.stderr)
                token_info = self._get_token(grant_type="client_credentials", scope=self._client_credentials_scope)
                if self.token_file:
                    save_token(token_info, self.token_file)
                return True, None
        except KrogerAPIError as e:
            return False, f"Getting a new token failed: {e.message.splitlines()[0]}"
        return False, "There is no refresh token or client-credentials scope to get a new token with."
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None,
                    headers: Optional[Dict] = None) -> Union[Dict[str, Any], None]:
        """
        Make a request to the Kroger API
        
        Args:
            method: The HTTP method (GET, POST, PUT, etc.)
            endpoint: The API endpoint
            params: Query parameters
            data: Request body data
            headers: Additional HTTP headers
            
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
        
        def send() -> requests.Response:
            # Combine default authorization headers with any additional headers
            request_headers = self._get_auth_header()
            if headers:
                request_headers.update(headers)
            # Use json parameter to automatically set Content-Type
            return self._send(method, url, params=params, json=data, headers=request_headers)
        
        response = send()
            
        note = None
        if response.status_code == 401:
            recovered, note = self._recover_from_unauthorized()
            if recovered:
                response = send()
                if response.status_code == 401:
                    note = "The request was retried once with a new token and was rejected again."
            
        if not response.ok:
            raise error_from_response(response, note=note)
                
        return self._parse_json(response)
