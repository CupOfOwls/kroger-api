"""
Token storage utility for Kroger API client.
This module provides functions to save and load OAuth tokens to avoid repeated logins.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default token file location
TOKEN_FILE = ".kroger_tokens.json"

# File that user (authorization-code) tokens are saved to. kroger-mcp reads
# the same file.
USER_TOKEN_FILE = ".kroger_token_user.json"

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

    The token is written to a temporary file that only the owner can read
    (mode 600 from the start), which then replaces the old file. A reader,
    such as another process that shares the token, never sees a
    half-written file.
    
    Args:
        token_info: The token information returned from the API
        token_file: The file path to save the token to
    """
    token_file = get_token_file_path(token_file)

    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(token_file), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(token_info, f, indent=2)
        os.replace(temp_path, token_file)
    except BaseException:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


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

        # Token files written before 0.4.0 have no expires_at. The file is
        # written when the token is issued, so its mtime marks the start of
        # the token's lifetime.
        if isinstance(token_info, dict) and "expires_at" not in token_info and token_info.get("expires_in") is not None:
            try:
                token_info["expires_at"] = os.path.getmtime(token_file) + float(token_info["expires_in"])
            except (OSError, TypeError, ValueError):
                pass

        return token_info
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Could not load the token file %s: %s", token_file, e)
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
        logger.info("Deleted the token file %s", token_file)


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
