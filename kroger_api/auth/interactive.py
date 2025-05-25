"""
Interactive authentication utilities for Kroger API client.
This module provides functions for interactive authentication flows.
"""
import os
import threading
import time
from typing import Dict, Any, Tuple, Optional

from ..utils.oauth import (
    start_oauth_server,
    extract_port_from_redirect_uri,
    generate_random_state,
    open_browser_for_auth
)
from ..utils.env import get_redirect_uri
from ..kroger_api import KrogerAPI
from ..token_storage import load_token, get_refresh_token

def authenticate_user(scopes: str = "cart.basic:write profile.compact", 
                      token_file: str = ".kroger_token_user.json", 
                      timeout: int = 120) -> KrogerAPI:
    """
    Authenticate a user and return a KrogerAPI client with valid tokens
    
    This function implements the complete OAuth2 authorization code flow,
    including token refresh and browser-based authorization.
    
    Args:
        scopes: The OAuth scopes to request
        token_file: The file to store the token in
        timeout: The timeout for waiting for the authorization code (in seconds)
        
    Returns:
        A KrogerAPI instance with valid tokens
        
    Raises:
        TimeoutError: If the authorization flow times out
        ValueError: If the authentication fails for other reasons
    """
    # Initialize the API client
    kroger = KrogerAPI()
    
    # Set the token file
    kroger.client.token_file = token_file
    
    # Try to load a saved token and test if it's valid
    token_info = load_token(token_file)
    if token_info:
        kroger.client.token_info = token_info
        
        # Test if the token is valid
        try:
            print("Found saved token, testing if it's still valid...")
            is_valid = kroger.test_current_token()
            if is_valid:
                print("Token is valid - no need to log in again!")
                return kroger
        except Exception:
            print("Token validation failed, will try to refresh")
            # Token is invalid, continue with the flow
            pass
            
    # If token is invalid, try to refresh it
    try:
        refresh_token = get_refresh_token(token_file)
        if refresh_token:
            print("Refreshing token...")
            token_info = kroger.authorization.refresh_token(refresh_token)
            # Test the refreshed token
            is_valid = kroger.test_current_token()
            if is_valid:
                print("Token refreshed successfully.")
                return kroger
    except Exception as e:
        print(f"Token refresh failed: {e}")
        print("Will proceed with new authorization...")
        # Refresh failed, continue with the full authorization flow
        pass
        
    print("Starting new OAuth authorization flow...")
    
    # Extract the port from the redirect URI
    redirect_uri = get_redirect_uri()
    port = extract_port_from_redirect_uri(redirect_uri)
    
    # Variables to store the authorization code
    auth_code = None
    auth_state = None
    auth_event = threading.Event()
    
    # Callback for when the authorization code is received
    def on_code_received(code, state):
        nonlocal auth_code, auth_state
        auth_code = code
        auth_state = state
        auth_event.set()
    
    # Start the server to handle the OAuth2 redirect
    server, _ = start_oauth_server(port, on_code_received)
    
    try:
        # Generate a random state value for security
        state = generate_random_state()
        
        # Get the authorization URL with the required scopes
        auth_url = kroger.authorization.get_authorization_url(
            scope=scopes,
            state=state
        )
        
        # Open the authorization URL in the default browser
        open_browser_for_auth(auth_url)
        
        # Wait for the authorization code (timeout after specified seconds)
        print(f"Waiting for authorization... (timeout: {timeout} seconds)")
        if not auth_event.wait(timeout):
            raise TimeoutError("Authorization flow timed out. Please try again.")
        
        # Verify the state parameter to prevent CSRF attacks
        if auth_state != state:
            raise ValueError("State parameter mismatch. Possible CSRF attack.")
        
        # Exchange the authorization code for an access token
        print("Authorization code received, exchanging for access token...")
        token_info = kroger.authorization.get_token_with_authorization_code(auth_code)
        
        print("Authentication successful.")
        return kroger
        
    except Exception as e:
        # Ensure the server is shut down, then re-raise the exception
        server.shutdown()
        raise e
    finally:
        # Ensure the server is shut down
        server.shutdown()

def switch_to_client_credentials(kroger: KrogerAPI, scope: str = "product.compact") -> Tuple[KrogerAPI, Dict, str]:
    """
    Switch the KrogerAPI client to use client credentials flow
    
    This is useful when switching from user token to client credentials
    for operations that don't require user authentication.
    
    This function DOES NOT modify the kroger.client.user_token_info or similar attributes.
    Instead, it returns the original token info for the caller to manage.
    
    Args:
        kroger: The KrogerAPI instance
        scope: The scope to request
        
    Returns:
        A tuple containing:
        - The same KrogerAPI instance with updated token
        - The original token_info (or None)
        - The original token_file (or None)
    """
    # Save the current token info and file for later
    user_token_info = None
    user_token_file = None
    
    if hasattr(kroger.client, 'token_info'):
        user_token_info = kroger.client.token_info
    
    if hasattr(kroger.client, 'token_file'):
        user_token_file = kroger.client.token_file
        
    # Get a client credentials token
    kroger.authorization.get_token_with_client_credentials(scope)
    
    # Return the kroger instance and the saved token info
    return kroger, user_token_info, user_token_file
