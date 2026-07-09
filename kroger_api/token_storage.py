"""
Token storage utility for Kroger API client.
This module provides functions to save and load OAuth tokens to avoid repeated logins.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default token file location
TOKEN_FILE = ".kroger_tokens.json"

def get_token_file_path(token_name) -> str:
    """Get the appropriate path for storing the token file.

    Resolution order:
      1. If token_name is already an absolute path, use it as-is.
      2. If KROGER_TOKEN_DIR is set, store the file there.
      3. Otherwise use the platform data directory (XDG spec on Unix,
         APPDATA on Windows) under a 'kroger-mcp' subdirectory, which is
         shared with the kroger-mcp package so both reuse the same tokens.
    """
    if os.path.isabs(token_name):
        return token_name

    env_dir = os.environ.get('KROGER_TOKEN_DIR')
    if env_dir:
        token_dir = Path(env_dir).expanduser()
    elif os.name == 'nt': # Windows
        token_dir = Path(os.environ.get('APPDATA', Path.home())) / 'kroger-mcp'
    else: # Unix-like
        token_dir = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'kroger-mcp'

    token_dir.mkdir(parents=True, exist_ok=True)
    return str(token_dir / token_name)




def save_token(token_info: Dict[str, Any], token_file: str = TOKEN_FILE) -> None:
    """
    Save a token to a file.
    
    Args:
        token_info: The token information returned from the API
        token_file: The file path to save the token to
    """


    token_file = get_token_file_path(token_file)

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

    token_file = get_token_file_path(token_file)

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

    token_file = get_token_file_path(token_file)


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

    token_file = get_token_file_path(token_file)

    token_info = load_token(token_file)
    
    if token_info and "refresh_token" in token_info:
        return token_info["refresh_token"]
    
    return None
