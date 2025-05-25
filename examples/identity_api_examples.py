#!/usr/bin/env python3
"""
Example script demonstrating the Identity API endpoint.
This requires the OAuth2 authorization flow with user interaction.
"""

import os
import sys
import json

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kroger_api.kroger_api import KrogerAPI
from kroger_api.auth import authenticate_user
from kroger_api.utils.env import load_and_validate_env


def pretty_print(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))


def main():
    """Demonstrate the Identity API endpoint"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET", "KROGER_REDIRECT_URI"])
        
        # Authenticate and get the Kroger client
        print("Authenticating with Kroger...")
        kroger = authenticate_user(scopes="profile.compact")
        
        # Example 1: Get user profile
        print("\n============ EXAMPLE 1: GET USER PROFILE ============")
        print("Getting user profile information...")
        
        try:
            profile = kroger.identity.get_profile()
            
            if profile and "data" in profile:
                profile_id = profile["data"].get("id", "N/A")
                print(f"User Profile ID: {profile_id}")
                print("\nNote: The Kroger Identity API only provides the profile ID.")
                print("This ID can be used with other APIs that require user identification.")
            else:
                print("Failed to get user profile information.")
                
            # Example 2: Demonstrate token refresh
            print("\n============ EXAMPLE 2: DEMONSTRATE TOKEN REFRESH ============")
            print("Testing token validity...")
            
            is_valid = kroger.test_current_token()
            print(f"Token is valid: {is_valid}")
            
            if is_valid and "refresh_token" in kroger.client.token_info:
                print("\nYou have a valid token with a refresh token.")
                print("This means you can make API requests without logging in again for an extended period.")
                print("When the access token expires, the client will automatically use the refresh token to get a new one.")
            elif is_valid:
                print("\nYou have a valid token but no refresh token.")
                print("When this token expires, you'll need to log in again.")
            else:
                print("\nYour token appears to be invalid.")
                print("Please run the script again to get a new token.")
        
        except Exception as e:
            print(f"Error accessing Identity API: {e}")
            print("This could be due to an invalid token or a network issue.")
            print("You can try running the script again to get a new token.")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
