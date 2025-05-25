#!/usr/bin/env python3
"""
Example script demonstrating all Authorization API endpoints.
"""

import os
import sys
import json
import base64
import time
import threading
import webbrowser

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kroger_api.kroger_api import KrogerAPI
from kroger_api.utils.env import load_and_validate_env, get_redirect_uri
from kroger_api.utils.oauth import start_oauth_server, generate_random_state, extract_port_from_redirect_uri


def pretty_print(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))


def main():
    """Demonstrate all Authorization API endpoints"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"])
        
        # Initialize the API client
        kroger = KrogerAPI()
        
        # Example 1: Client Credentials Flow
        print("\n============ EXAMPLE 1: CLIENT CREDENTIALS FLOW ============")
        print("This flow is used for accessing public data without user authentication.")
        print("Getting token with client credentials...")
        
        token_info = kroger.authorization.get_token_with_client_credentials("product.compact")
        
        # Display token information
        print("\nToken Information:")
        print(f"Access Token: {token_info['access_token'][:10]}... (truncated)")
        print(f"Token Type: {token_info['token_type']}")
        print(f"Expires In: {token_info['expires_in']} seconds")
        
        # Example 2: Generate Authorization URL
        print("\n============ EXAMPLE 2: GENERATE AUTHORIZATION URL ============")
        print("This is the first step in the Authorization Code flow.")
        print("It generates a URL where the user can log in and authorize your application.")
        
        try:
            # Try to get the redirect URI, but don't raise an error if it's not available
            redirect_uri = get_redirect_uri()
            scope = "cart.basic:write profile.compact"
            state = "random_state_string"
            banner = "kroger"  # The banner to display on the login page
            
            auth_url = kroger.authorization.get_authorization_url(
                scope=scope,
                state=state,
                banner=banner
            )
            
            print(f"\nAuthorization URL:\n{auth_url}")
            print("\nThis URL would be opened in a browser, where the user would log in")
            print("and authorize your application to access their data.")
            
            # Example 3: Authorization Code Flow
            print("\n============ EXAMPLE 3: AUTHORIZATION CODE FLOW ============")
            print("This flow is used for accessing user-specific data with their authorization.")
            print("It requires a redirect URI to receive the authorization code.")
            
            try:
                # Extract the port from the redirect URI
                port = extract_port_from_redirect_uri(redirect_uri)
                
                # Generate a random state value for security
                state = generate_random_state()
                
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
                    # Get the authorization URL
                    auth_url = kroger.authorization.get_authorization_url(
                        scope="cart.basic:write profile.compact",
                        state=state
                    )
                    
                    # Ask if the user wants to open the URL
                    print("\nWould you like to open the authorization URL in your browser to test this flow?")
                    answer = input("This will require you to log in to your Kroger account (y/n): ")
                    
                    if answer.lower() == 'y':
                        # Open the authorization URL in the default browser
                        print(f"\nOpening the authorization URL in your browser...")
                        webbrowser.open(auth_url)
                        
                        # Wait for the authorization code (timeout after 2 minutes)
                        print("Waiting for authorization... Please log in and authorize the application.")
                        auth_event.wait(timeout=120)
                        
                        if not auth_code:
                            print("Authorization timed out.")
                        else:
                            # Verify the state parameter to prevent CSRF attacks
                            if auth_state != state:
                                print(f"State mismatch. Expected {state}, got {auth_state}.")
                                print("This could be a security issue.")
                            else:
                                # Exchange the authorization code for an access token
                                print("\nExchanging the authorization code for an access token...")
                                token_info = kroger.authorization.get_token_with_authorization_code(auth_code)
                                
                                # Display token information
                                print("\nToken Information:")
                                print(f"Access Token: {token_info['access_token'][:10]}... (truncated)")
                                print(f"Token Type: {token_info['token_type']}")
                                print(f"Expires In: {token_info['expires_in']} seconds")
                                print(f"Refresh Token: {token_info['refresh_token'][:10]}... (truncated)")
                                
                                # Example 4: Refresh Token Flow
                                print("\n============ EXAMPLE 4: REFRESH TOKEN FLOW ============")
                                print("This flow is used to get a new access token when the current one expires.")
                                print("It uses the refresh token from the Authorization Code flow.")
                                
                                # Get the refresh token
                                refresh_token = token_info['refresh_token']
                                
                                # Wait a moment to demonstrate the concept
                                print("\nWaiting 3 seconds to demonstrate the refresh token flow...")
                                time.sleep(3)
                                
                                # Refresh the token
                                print("\nRefreshing the token...")
                                new_token_info = kroger.authorization.refresh_token(refresh_token)
                                
                                # Display new token information
                                print("\nNew Token Information:")
                                print(f"Access Token: {new_token_info['access_token'][:10]}... (truncated)")
                                print(f"Token Type: {new_token_info['token_type']}")
                                print(f"Expires In: {new_token_info['expires_in']} seconds")
                                print(f"Refresh Token: {new_token_info['refresh_token'][:10]}... (truncated)")
                    else:
                        print("\nSkipping the authorization flow demonstration.")
                
                finally:
                    # Ensure the server is shut down
                    server.shutdown()
            
            except Exception as e:
                print(f"Error in Authorization Code Flow: {e}")
        
        except Exception as e:
            print(f"Missing KROGER_REDIRECT_URI environment variable. Skipping examples 2 and 3.")
        
        # Example 5: Understanding the Authorization Header
        print("\n============ EXAMPLE 5: UNDERSTANDING THE AUTHORIZATION HEADER ============")
        print("This example explains how the Authorization header is constructed for OAuth2.")
        
        # Client credentials for demonstration
        client_id = os.getenv("KROGER_CLIENT_ID")
        client_secret = os.getenv("KROGER_CLIENT_SECRET")
        
        # Create the Basic Auth header value
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_header = f"Basic {encoded_credentials}"
        
        print("\nFor token requests, the Authorization header is constructed as follows:")
        print("1. Combine the client_id and client_secret with a colon: client_id:client_secret")
        print("2. Base64 encode this string")
        print("3. Prepend 'Basic ' to the encoded string")
        
        print(f"\nExample with your credentials:")
        print(f"client_id: {client_id[:5]}... (truncated)")
        print(f"client_secret: {client_secret[:5]}... (truncated)")
        print(f"Combined: {client_id[:5]}...:{client_secret[:5]}... (truncated)")
        print(f"Encoded: {encoded_credentials[:20]}... (truncated)")
        print(f"Authorization header: Basic {encoded_credentials[:20]}... (truncated)")
        
        print("\nFor API requests, the Authorization header is constructed as follows:")
        print("1. Take the access_token from the token response")
        print("2. Prepend 'Bearer ' to the access_token")
        
        print(f"\nExample with your access token:")
        print(f"access_token: {token_info['access_token'][:10]}... (truncated)")
        print(f"Authorization header: Bearer {token_info['access_token'][:10]}... (truncated)")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
