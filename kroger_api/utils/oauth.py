"""
OAuth2 utilities for Kroger API client.
This module provides functions to handle the OAuth2 authorization flow.
"""
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import random
import string

class OAuth2Handler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 redirect"""

    def __init__(self, *args, code_callback=None, **kwargs):
        self.code_callback = code_callback
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET request"""
        # Parse the query parameters
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'code' in params:
            code = params['code'][0]
            state = params.get('state', [None])[0]

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body>
            <h1>Authorization Successful</h1>
            <p>You can close this window and return to the application.</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode())

            # Call the callback with the authorization code
            if self.code_callback:
                self.code_callback(code, state)
        else:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = """
            <html>
            <head><title>Authorization Failed</title></head>
            <body>
            <h1>Authorization Failed</h1>
            <p>No authorization code was received. Please try again.</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode())

    def log_message(self, format, *args):
        """Suppress logging"""
        pass

def start_oauth_server(port, code_callback):
    """
    Start a server to handle the OAuth2 redirect
    
    Args:
        port: The port to listen on
        code_callback: Function to call when an authorization code is received
        
    Returns:
        The server instance and server thread
    """
    # Create a custom request handler class with the callback
    class CustomHandler(OAuth2Handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, code_callback=code_callback, **kwargs)

    # Start the server
    server = HTTPServer(('localhost', port), CustomHandler)
    print(f"Started OAuth2 callback server on port {port}")

    # Run the server in a separate thread
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True  # Make the thread terminate when the main program exits
    thread.start()
    
    return server, thread

def extract_port_from_redirect_uri(redirect_uri):
    """
    Extract the port from a redirect URI
    
    Args:
        redirect_uri: The redirect URI
        
    Returns:
        The port number
    """
    try:
        port = int(redirect_uri.split(":")[-1].split("/")[0])
        return port
    except (ValueError, IndexError):
        raise ValueError(f"Could not extract port from redirect URI: {redirect_uri}")

def generate_random_state(length=16):
    """
    Generate a random state string for OAuth2 security
    
    Args:
        length: The length of the state string
        
    Returns:
        A random string
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def open_browser_for_auth(auth_url):
    """
    Open the default web browser for user authorization
    
    Args:
        auth_url: The authorization URL
    """
    print("\nOpening your browser to log in to your Kroger account...")
    print(f"Authorization URL: {auth_url}\n")
    webbrowser.open(auth_url)
    print("If your browser does not open automatically, copy and paste the URL above into your browser.")
