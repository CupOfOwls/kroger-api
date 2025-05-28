#!/usr/bin/env python3
"""
Example of the OAuth 2.0 authorization code flow with PKCE
"""

import os
import time
import webbrowser
from dotenv import load_dotenv
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import secrets

from kroger_api import KrogerAPI
from kroger_api.utils import generate_pkce_parameters

# Load environment variables
load_dotenv()

# Check required environment variables
required_env_vars = ["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET", "KROGER_REDIRECT_URI"]
missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_env_vars:
    print(f"Missing required environment variables: {', '.join(missing_env_vars)}")
    print("Please set them in a .env file or as environment variables.")
    exit(1)

# Extract port from redirect URI for the callback server
redirect_uri = os.getenv("KROGER_REDIRECT_URI")
parsed_uri = urlparse(redirect_uri)
if not parsed_uri.port:
    port = 8000  # Default port
else:
    port = parsed_uri.port

# Global variables for OAuth callback
auth_code = None
auth_state = None
auth_error = None
auth_event = threading.Event()

# Generate a state parameter for CSRF protection
state = secrets.token_urlsafe(16)

# Generate PKCE parameters
pkce_params = generate_pkce_parameters()
print(f"\nGenerated PKCE parameters:")
print(f"  Code Verifier: {pkce_params['code_verifier'][:10]}...{pkce_params['code_verifier'][-10:]}")
print(f"  Code Challenge: {pkce_params['code_challenge']}")
print(f"  Method: {pkce_params['code_challenge_method']}")

# Handler for the OAuth callback
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth callback"""
        global auth_code, auth_state, auth_error
        
        # Parse the query parameters
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        # Check for errors
        if "error" in params:
            auth_error = params["error"][0]
            if "error_description" in params:
                auth_error += f": {params['error_description'][0]}"
        
        # Check for authorization code
        elif "code" in params:
            auth_code = params["code"][0]
            if "state" in params:
                auth_state = params["state"][0]
        
        # Send a response to the browser
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        # Create a nice HTML response
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Kroger API Authorization</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }
                .success {
                    color: green;
                    font-weight: bold;
                }
                .error {
                    color: red;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
        """
        
        if auth_error:
            html += f"""
            <h1>Authorization Failed</h1>
            <p class="error">{auth_error}</p>
            <p>Please close this window and try again.</p>
            """
        else:
            html += """
            <h1>Authorization Successful</h1>
            <p class="success">You have successfully authorized the application.</p>
            <p>You can now close this window and return to the application.</p>
            """
        
        html += """
        </body>
        </html>
        """
        
        self.wfile.write(html.encode())
        
        # Signal that we've received the callback
        auth_event.set()
    
    def log_message(self, format, *args):
        """Suppress server logs"""
        return


def main():
    # Initialize the Kroger API client
    kroger = KrogerAPI()
    
    # Start the callback server
    try:
        server = HTTPServer(("localhost", port), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"\nStarted callback server on port {port}")
    except Exception as e:
        print(f"Error starting callback server: {e}")
        return
    
    try:
        # Get the authorization URL with PKCE
        auth_url = kroger.authorization.get_authorization_url(
            scope="cart.basic:write profile.compact",
            state=state,
            code_challenge=pkce_params["code_challenge"],
            code_challenge_method=pkce_params["code_challenge_method"]
        )
        
        print("\n" + "="*60)
        print("KROGER API AUTHORIZATION WITH PKCE")
        print("="*60)
        print("Opening your browser for authorization...")
        print(f"Authorization URL: {auth_url}")
        print("="*60 + "\n")
        
        # Open the authorization URL in the browser
        webbrowser.open(auth_url)
        
        # Wait for the callback (with a timeout)
        if not auth_event.wait(timeout=300):
            print("Authorization timed out after 5 minutes.")
            return
        
        # Check for errors
        if auth_error:
            print(f"Authorization failed: {auth_error}")
            return
        
        # Check for code and state
        if not auth_code:
            print("No authorization code received.")
            return
        
        # Verify state to prevent CSRF attacks
        if auth_state != state:
            print(f"State mismatch. Expected {state}, got {auth_state}.")
            return
        
        print("Authorization code received. Exchanging for token...")
        
        # Exchange the authorization code for a token with the code verifier
        token_info = kroger.authorization.get_token_with_authorization_code(
            auth_code,
            code_verifier=pkce_params["code_verifier"]
        )
        
        # Check the token
        if not token_info or "access_token" not in token_info:
            print("Failed to get access token.")
            return
        
        # Success!
        print("\n" + "="*60)
        print("AUTHORIZATION SUCCESSFUL!")
        print("="*60)
        print(f"Access token: {token_info['access_token'][:10]}...{token_info['access_token'][-10:]}")
        print(f"Token type: {token_info.get('token_type', 'N/A')}")
        print(f"Expires in: {token_info.get('expires_in', 'N/A')} seconds")
        print(f"Scope: {token_info.get('scope', 'N/A')}")
        
        if "refresh_token" in token_info:
            print(f"Refresh token: {token_info['refresh_token'][:10]}...{token_info['refresh_token'][-10:]}")
        
        print("\nToken saved to .kroger_token_user.json")
        print("You can now use the other examples that require authentication.")
        print("="*60)
        
        # Demonstrate token usage by getting user profile
        try:
            profile = kroger.identity.get_profile()
            print("\nSuccessfully retrieved user profile!")
            print(f"User ID: {profile['data'].get('id', 'N/A')}")
        except Exception as e:
            print(f"\nFailed to get user profile: {e}")
        
        # Let the user see the results before exiting
        print("\nPress Enter to exit...")
        input()
    
    finally:
        # Shut down the server
        server.shutdown()
        server.server_close()
        print("Server shut down.")


if __name__ == "__main__":
    main()
