#!/usr/bin/env python3
"""
Example script demonstrating the improved token refresh functionality.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kroger_api.kroger_api import KrogerAPI
from kroger_api.token_storage import load_token, save_token, clear_token
from kroger_api.utils.env import get_zip_code


def pretty_print(data):
    """Print JSON data in a readable format"""
    import json
    print(json.dumps(data, indent=2))


def main():
    """Demonstrate the improved token refresh functionality"""
    # Load environment variables from .env file
    load_dotenv()

    # Check if environment variables are set
    required_vars = ["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"Error: {var} environment variable is not set.")
            print("Please set it in a .env file or in your environment.")
            sys.exit(1)

    # Initialize the API client
    kroger = KrogerAPI()

    # Example 1: Client Credentials Flow with token testing
    print("\n===== Example 1: Client Credentials Flow with token testing =====")

    # First try to load an existing token
    token_file = ".kroger_token_client_product.compact.json"
    token_info = load_token(token_file)

    if token_info:
        print("Found existing client token, testing if it's valid...")
        
        # Test if the token is valid
        kroger.client.token_info = token_info
        is_valid = kroger.test_current_token()
        
        if is_valid:
            print("Token is valid, no need to get a new one")
        else:
            print("Token is invalid, getting a new one...")
            token_info = kroger.authorization.get_token_with_client_credentials("product.compact")
            print("New token obtained")
    else:
        print("No existing token found, getting a new one...")
        token_info = kroger.authorization.get_token_with_client_credentials("product.compact")
        print("New token obtained")

    # Display token information
    print("\nToken Information:")
    pretty_print(token_info)

    # Example 2: Testing token refresh functionality
    if "refresh_token" in token_info:
        print("\n===== Example 2: Testing token refresh functionality =====")
        print("This token has a refresh token, refreshing it...")
        
        refresh_token = token_info["refresh_token"]
        try:
            new_token_info = kroger.authorization.refresh_token(refresh_token)
            print("Token refreshed successfully")
            
            print("\nNew Token Information:")
            pretty_print(new_token_info)
        except Exception as e:
            print(f"Failed to refresh token: {e}")
    else:
        print("\nThe client credentials token doesn't have a refresh token.")
        print("To test refresh token functionality, you need to use the authorization code flow.")

    # Example 3: Making an API request with automatic token refresh
    print("\n===== Example 3: Making an API request with automatic token refresh =====")
    print("Making a request to the Locations API...")
    
    # If the token is invalid, it will be automatically refreshed
    try:
        locations = kroger.location.search_locations(zip_code=get_zip_code(), limit=1)
        print("Request successful, got locations:")
        pretty_print(locations)
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    main()
