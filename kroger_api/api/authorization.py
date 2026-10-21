import logging
from typing import Dict, Optional, Any

from kroger_api.client import KrogerClient
from kroger_api.errors import BadRequestError
from kroger_api.token_storage import USER_TOKEN_FILE, get_refresh_token, load_token

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
    
    def get_token_with_authorization_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an access token using an authorization code
        
        Args:
            code: The authorization code received from the redirect
            code_verifier: PKCE code verifier used during authorization (if PKCE was used)
            
        Returns:
            The token information
        """
        return self.client.get_token_with_authorization_code(code, code_verifier)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token received from a previous token request
            
        Returns:
            The token information
        """
        return self.client.refresh_token(refresh_token)
    
    def refresh_token_if_needed(self, token_file: str = None) -> Optional[Dict[str, Any]]:
        """
        Load a saved token into the client, refreshing it first if it has expired
        
        Args:
            token_file: The file path to load the token from
        
        Returns:
            The token information (either existing or refreshed), or None if
            there is no saved token, or it has expired and cannot be refreshed

        Raises:
            KrogerAPIError: If refreshing fails for another reason than a
                rejected refresh token, such as a network error
        """
        token_file = token_file or self.client.token_file or USER_TOKEN_FILE
        
        # Load the token
        token_info = load_token(token_file)
        if not token_info:
            return None

        # A refreshed token is saved back to the file it was loaded from
        self.client.token_file = token_file
        
        # Use the saved token while it is unexpired
        if not self.client.is_token_expired(token_info):
            self.client.token_info = token_info
            return token_info
            
        refresh_token = token_info.get("refresh_token") or get_refresh_token(token_file)
        if not refresh_token:
            return None
        try:
            return self.refresh_token(refresh_token)
        except BadRequestError:
            return None
