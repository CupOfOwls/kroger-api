"""
Token storage utility for Kroger API client.
This module provides functions to save and load OAuth tokens to avoid repeated logins.
"""

import os
import json
from typing import Dict, Any, Optional

# Default token file location
TOKEN_FILE = ".kroger_tokens.json"


def save_token(token_info: Dict[str, Any], token_file: str = TOKEN_FILE) -> None:
    """
    Save a token to a file.
    
    Args:
        token_info: The token information returned from the API
        token_file: The file path to save the token to
    """
    # Save to file
    with open(token_file, "w") as f:
        json.dump(token_info, f, indent=2)
    
    # Set file permissions to 600 (only owner can read/write)
    os.chmod(token_file, 0o600)


def load_token(token_file: str = TOKEN_FILE) -> Optional[Dict[str, Any]]:
    """
    Load a token from a file if it exists.
    
    Args:
        token_file: The file path to load the token from
        
    Returns:
        The token information or None if not available
    """
    if not os.path.exists(token_file):
        return None
    
    try:
        with open(token_file, "r") as f:
            token_info = json.load(f)
        
        print(f"Found saved token, will test if it's still valid...")
        return token_info
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading token: {e}")
        return None


def clear_token(token_file: str = TOKEN_FILE) -> None:
    """
    Delete the token file if it exists.
    
    Args:
        token_file: The file path to delete
    """
    if os.path.exists(token_file):
        os.remove(token_file)
        print("Token file deleted.")


def get_refresh_token(token_file: str = TOKEN_FILE) -> Optional[str]:
    """
    Get the refresh token from a token file if it exists.
    
    Args:
        token_file: The file path to load the token from
        
    Returns:
        The refresh token or None if not available
    """
    token_info = load_token(token_file)
    
    if token_info and "refresh_token" in token_info:
        return token_info["refresh_token"]
    
    return None
