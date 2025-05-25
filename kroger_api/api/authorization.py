from typing import Dict, Optional, Any

from kroger_api.client import KrogerClient
from kroger_api.token_storage import get_refresh_token, load_token


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
    
    def get_authorization_url(self, scope: str, state: Optional[str] = None, banner: Optional[str] = None) -> str:
        """
        Get the URL to redirect the user to for authorization
        
        Args:
            scope: The level of access your application is requesting
            state: A random string to verify that the response belongs to the initiated request
            banner: Sets the chain specific branding displayed on the authorization consent screen
            
        Returns:
            The authorization URL
        """
        return self.client.get_authorization_url(scope, state, banner)
    
    def get_token_with_client_credentials(self, scope: str) -> Dict[str, Any]:
        """
        Get an access token using client credentials
        
        Args:
            scope: The level of access your application is requesting
            
        Returns:
            The token information
        """
        return self.client.get_token_with_client_credentials(scope)
    
    def get_token_with_authorization_code(self, code: str) -> Dict[str, Any]:
        """
        Get an access token using an authorization code
        
        Args:
            code: The authorization code received from the redirect
            
        Returns:
            The token information
        """
        return self.client.get_token_with_authorization_code(code)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token received from a previous token request
            
        Returns:
            The token information
        """
        return self.client.refresh_token(refresh_token)
    
    def refresh_token_if_needed(self, token_file: str = None) -> Dict[str, Any]:
        """
        Check if the token needs refreshing and refresh it if necessary
        
        Args:
            token_file: The file path to load the token from
        
        Returns:
            The token information (either existing or refreshed)
        """
        # Determine which token file to use
        if token_file is None:
            if self.client.token_file:
                token_file = self.client.token_file
            else:
                token_file = ".kroger_token_user.json"
        
        # Load the token
        token_info = load_token(token_file)
        
        if token_info:
            # Test if the token is valid
            if self.client.test_token(token_info):
                # Token is valid, return it
                return token_info
            
            # Token is invalid, check if we have a refresh token
            refresh_token = get_refresh_token(token_file)
            if refresh_token:
                # Try to refresh the token
                try:
                    return self.refresh_token(refresh_token)
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
        
        # If we couldn't refresh or there was no token, return None
        return None
