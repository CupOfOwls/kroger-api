import logging
from typing import Dict, Optional, Any

from kroger_api.client import KrogerClient
from kroger_api.errors import BadRequestError, NotAuthenticatedError
from kroger_api.token_storage import USER_TOKEN_FILE, get_token_file_path, load_token

logger = logging.getLogger(__name__)


class AuthorizationAPI:
    """
    Provides access to the Kroger Authorization API endpoints.
    """ 
    
    def __init__(self, client: KrogerClient):
        """
        Initialize the Authorization API
        
        Args:
            client: The KrogerClient instance
        """
        self.client = client
    
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
        """
        return self.client.get_authorization_url(scope, state, banner, code_challenge, code_challenge_method)
    
    def get_token_with_client_credentials(self, scope: str) -> Dict[str, Any]:
        """
        Get an access token using client credentials
        
        Args:
            scope: The level of access your application is requesting
            
        Returns:
            The token information
        """
        return self.client.get_token_with_client_credentials(scope)
    
    def get_token_with_authorization_code(self, code: str, code_verifier: Optional[str] = None,
                                          token_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an access token using an authorization code
        
        Args:
            code: The authorization code received from the redirect
            code_verifier: PKCE code verifier used during authorization (if PKCE was used)
            token_file: The file to save the user token to (default USER_TOKEN_FILE)
            
        Returns:
            The token information
        """
        return self.client.get_token_with_authorization_code(code, code_verifier, token_file)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token received from a previous token request
            
        Returns:
            The token information
        """
        return self.client.refresh_token(refresh_token)
    
    def load_saved_token(self, token_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a saved user token into the client, renewing it first if it has expired

        An expired token is renewed with the token file locked, so threads
        and processes that share the file renew it one at a time. One that
        waited for the lock uses the token that another renewed meanwhile,
        instead of sending a refresh token that was already used.

        Args:
            token_file: The file to load the token from (default the client's
                token file, else USER_TOKEN_FILE). A renewed token is saved
                back to it, and it becomes the client's token file.

        Returns:
            The token information, now in the client

        Raises:
            NotAuthenticatedError: If there is no saved token, or it has
                expired and has no refresh token, or it was deleted while
                this call waited to renew it
            BadRequestError: If Kroger rejected the refresh token, so the
                user has to sign in again
            KrogerAPIError: If renewing fails for another reason, such as a
                network error
        """
        token_file = token_file or self.client.token_file or USER_TOKEN_FILE
        token_info = load_token(token_file)
        if not isinstance(token_info, dict) or not token_info.get("access_token"):
            raise NotAuthenticatedError(f"There is no saved token in {get_token_file_path(token_file)}.")

        # The client's token file changes only when its token comes from this
        # file, so a token that cannot be used never redirects later saves.
        if not self.client.is_token_expired(token_info):
            self.client.token_info = token_info
            self.client.token_file = token_file
            return token_info
        if not token_info.get("refresh_token"):
            raise NotAuthenticatedError(
                f"The saved token in {get_token_file_path(token_file)} has expired and has no refresh token."
            )

        # token_info has a refresh token, so this renews it or raises
        renewed = self.client._renew_user_token(token_file, token_info)
        self.client.token_file = token_file
        return renewed

    def refresh_token_if_needed(self, token_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load a saved token into the client, refreshing it first if it has expired

        Like load_saved_token, but returns None where that raises
        NotAuthenticatedError or BadRequestError.

        Args:
            token_file: The file path to load the token from

        Returns:
            The token information (either existing or refreshed), or None if
            there is no saved token, or it has expired and cannot be refreshed

        Raises:
            KrogerAPIError: If refreshing fails for another reason than a
                rejected refresh token, such as a network error
        """
        try:
            return self.load_saved_token(token_file)
        except (NotAuthenticatedError, BadRequestError):
            return None
