#!/usr/bin/env python3
"""
Example script demonstrating the OAuth2 authorization code flow with the Kroger API.

This script shows how to use our authentication abstractions to get and use OAuth tokens.
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
    """Main function demonstrating the OAuth flow"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET", "KROGER_REDIRECT_URI"])
        
        # Authenticate and get the Kroger client
        print("Authenticating with Kroger...")
        kroger = authenticate_user(scopes="cart.basic:write profile.compact")
        
        # At this point, we have a valid token that can be used for API calls
        
        # Example 1: Get the user's profile
        print("\n============ EXAMPLE 1: USING THE IDENTITY API ============")
        print("Getting the user's profile...")
        try:
            profile = kroger.identity.get_profile()
            pretty_print(profile)
        except Exception as e:
            print(f"Error getting profile: {e}")
        
        # Example 2: Add an item to the cart
        print("\n============ EXAMPLE 2: USING THE CART API ============")
        print("Adding an item to the cart...")
        try:
            kroger.cart.add_to_cart([
                {
                    "upc": "0001111060903",  # Example UPC
                    "quantity": 1,
                    "modality": "PICKUP"
                }
            ])
            print("Item added to cart successfully!")
        except Exception as e:
            print(f"Error adding item to cart: {e}")
        
        # Example 3: Demonstrate manual token refresh (normally handled automatically)
        print("\n============ EXAMPLE 3: DEMONSTRATING TOKEN REFRESH ============")
        
        if "refresh_token" in kroger.client.token_info:
            refresh_token = kroger.client.token_info["refresh_token"]
            print(f"Current refresh token: {refresh_token[:10]}...")
            
            print("Refreshing the token...")
            try:
                new_token_info = kroger.authorization.refresh_token(refresh_token)
                print(f"Got new access token: {new_token_info['access_token'][:10]}...")
                print(f"Got new refresh token: {new_token_info['refresh_token'][:10]}...")
                
                # Verify the new token works
                print("\nVerifying the new token works...")
                try:
                    profile = kroger.identity.get_profile()
                    profile_id = profile.get("data", {}).get("id", "Unknown")
                    print(f"User profile ID: {profile_id}")
                    print("New token is working correctly!")
                except Exception as e:
                    print(f"Error getting profile with new token: {e}")
            except Exception as e:
                print(f"Error refreshing token: {e}")
        else:
            print("No refresh token available, cannot demonstrate token refresh.")
        
        # Example 4: How automatic token refresh works
        print("\n============ EXAMPLE 4: AUTOMATIC TOKEN REFRESH ============")
        print("In a real application, tokens are automatically refreshed when they expire.")
        print("The authentication module handles this for you behind the scenes.")
        print("When you make an API call and the token is expired:")
        print("1. The client detects the 401 Unauthorized error")
        print("2. It automatically tries to refresh the token using the refresh token")
        print("3. If successful, it retries the original API call with the new token")
        print("4. If the refresh fails, it raises an exception")
        
        # Show how to use the token in other applications
        print("\n============ USING TOKENS IN OTHER APPLICATIONS ============")
        print("The token is saved to a file (default: '.kroger_token_user.json')")
        print("You can use this token in other applications by loading it from this file.")
        print("The token management system in the kroger_api package handles:")
        print("- Saving tokens to disk")
        print("- Loading tokens from disk")
        print("- Testing if tokens are still valid")
        print("- Refreshing tokens when they expire")
        print("- Automatic retry of API calls when tokens are refreshed")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
