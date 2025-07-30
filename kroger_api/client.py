import os
import base64
import requests
from typing import Dict, Optional, Any, Union, Tuple
from urllib.parse import urljoin
from dotenv import load_dotenv

# Import the token storage module
try:
    from kroger_api.token_storage import save_token, load_token, get_refresh_token
except ImportError:
    # For backwards compatibility
    save_token = lambda token_info, token_file=None: None
    load_token = lambda token_file=None: None
    get_refresh_token = lambda token_file=None: None

load_dotenv()

class KrogerClient:
    """
    Base client for interacting with the Kroger API
    """
    BASE_URL = "https://api.kroger.com"
     
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None):
        """
        Initialize the Kroger API client
        
        Args:
            client_id: Your Kroger API client ID
            client_secret: Your Kroger API client secret
            redirect_uri: The redirect URI registered with your Kroger API application
        """
        self.client_id = client_id or os.getenv("KROGER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("KROGER_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("KROGER_REDIRECT_URI")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing Kroger API credentials. Please provide client_id and client_secret.")
        
        self.token_info = None
        self.token_file = None
    
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
        """
        # Set the token file for this scope
        self.token_file = f".kroger_token_client_{scope.replace(':', '_')}.json"
        
        # Try to load an existing token first
        token_info = load_token(self.token_file)
        if token_info:
            # Test if the token is valid before using it
            if self.test_token(token_info):
                self.token_info = token_info
                return token_info
            
            # If token is invalid, get a new one
            print("Token appears invalid, requesting a new one")
            
        # If no valid token exists, get a new one
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
        """
        if not self.redirect_uri:
            raise ValueError("Missing redirect_uri for authorization code flow")
        
        # Set the token file for user tokens
        self.token_file = f".kroger_token_user.json"
        
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
        """
        try:
            token_info = self._get_token(
                grant_type="refresh_token",
                refresh_token=refresh_token
            )
            
            # Save the refreshed token
            if self.token_file:
                save_token(token_info, self.token_file)
            else:
                save_token(token_info, f".kroger_token_user.json")
            
            return token_info
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Invalid refresh token
                print("Invalid refresh token. Please re-authenticate.")
            raise
    
    def test_token(self, token_info: Dict[str, Any]) -> bool:
        """
        Test if a token is valid by making a simple API request
        
        Args:
            token_info: The token information
            
        Returns:
            True if the token is valid, False otherwise
        """
        # If we have a refresh token, try to use it if direct validation fails
        if "refresh_token" in token_info:
            # Make a simple API request to verify the token
            try:
                # Temporarily set the token_info to test it
                original_token_info = self.token_info
                self.token_info = token_info
                
                # Make a simple request
                response = requests.get(
                    urljoin(self.BASE_URL, "/v1/connect/oauth2/profile"),
                    headers=self._get_auth_header()
                )
                
                # Restore original token_info
                self.token_info = original_token_info
                
                # If the request was successful, the token is valid
                if response.status_code == 200:
                    return True
                
                # If token is invalid and we have a refresh token, try to refresh
                try:
                    print("Token validation failed, attempting to refresh")
                    new_token_info = self.refresh_token(token_info["refresh_token"])
                    self.token_info = new_token_info
                    return True
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return False
            except Exception:
                # If the validation request failed, try the refresh token
                try:
                    print("Token validation request failed, attempting to refresh")
                    new_token_info = self.refresh_token(token_info["refresh_token"])
                    self.token_info = new_token_info
                    return True
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return False
        else:
            # If we don't have a refresh token, just validate the token directly
            try:
                # Temporarily set the token_info to test it
                original_token_info = self.token_info
                self.token_info = token_info
                
                # Make a simple request
                response = requests.get(
                    urljoin(self.BASE_URL, "/v1/connect/oauth2/profile"),
                    headers=self._get_auth_header()
                )
                
                # Restore original token_info
                self.token_info = original_token_info
                
                # If the request was successful, the token is valid
                return response.status_code == 200
            except Exception:
                # If there was an error, the token is invalid
                return False
    
    def _get_token(self, grant_type: str, **kwargs) -> Dict[str, Any]:
        """
        Get an access token
        
        Args:
            grant_type: The OAuth2 grant type
            **kwargs: Additional parameters for the token request
            
        Returns:
            The token information
        """
        url = urljoin(self.BASE_URL, "/v1/connect/oauth2/token")
        
        auth_header = self._get_basic_auth_header()
        
        data = {
            'grant_type': grant_type,
            **kwargs
        }
        
        response = requests.post(url, headers=auth_header, data=data)
        response.raise_for_status()
        
        self.token_info = response.json()
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
            ValueError: If there is no token information available
        """
        if not self.token_info or 'access_token' not in self.token_info:
            raise ValueError("No access token available. Please authenticate first.")
        
        return {
            'Authorization': f"Bearer {self.token_info['access_token']}",
            'Accept': 'application/json'
        }
    
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
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        # Combine default authorization headers with any additional headers
        request_headers = self._get_auth_header()
        if headers:
            request_headers.update(headers)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,  # Use json parameter to automatically set Content-Type
                headers=request_headers
            )
            
            response.raise_for_status()
            
            # Some endpoints return 204 No Content
            if response.status_code == 204:
                return None
                
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Check if the error is due to an invalid token (401 Unauthorized)
            if e.response.status_code == 401:
                error_data = e.response.json()
                
                # Check if the error is due to an expired or invalid token
                if error_data.get("error") == "invalid_token":
                    print("Token is invalid or has expired, attempting to refresh")
                    
                    # Try to refresh the token if we have a refresh token
                    if self.token_file:
                        refresh_token = get_refresh_token(self.token_file)
                        if refresh_token:
                            try:
                                # Refresh the token
                                self.token_info = self.refresh_token(refresh_token)
                                
                                # Retry the request with the new token
                                request_headers = self._get_auth_header()
                                if headers:
                                    request_headers.update(headers)
                                
                                response = requests.request(
                                    method=method,
                                    url=url,
                                    params=params,
                                    json=data,
                                    headers=request_headers
                                )
                                
                                response.raise_for_status()
                                
                                # Some endpoints return 204 No Content
                                if response.status_code == 204:
                                    return None
                                    
                                return response.json()
                            except Exception as refresh_error:
                                print(f"Failed to refresh token: {refresh_error}")
                                # Re-raise the original error if we couldn't refresh
                
            # If we couldn't handle the error, re-raise it
            raise
