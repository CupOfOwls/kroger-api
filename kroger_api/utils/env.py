"""
Environment variable utilities for Kroger API client.
This module provides functions to load and validate environment variables.
"""
import logging
import os
from typing import List, Dict
from dotenv import find_dotenv, load_dotenv

from kroger_api.errors import ConfigurationError

logger = logging.getLogger(__name__)


def load_env_file() -> None:
    """
    Load settings from a .env file in the working directory, if there is one

    Variables that are already set in the environment keep their values.
    The search starts in the working directory, not in the directory of the
    code that calls this, so a .env file next to an installed package or in
    a parent of the source tree is not read by accident.
    """
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path)


def load_and_validate_env(required_vars: List[str]) -> Dict[str, str]:
    """
    Load environment variables from .env file and validate required variables
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Dictionary of environment variables
        
    Raises:
        ConfigurationError: If any required environment variables are missing
            (a ValueError subclass)
    """
    load_env_file()
    
    # Check if required environment variables are set
    missing_vars = []
    env_vars = {}
    
    for var in required_vars:
        value = os.getenv(var)
        if value is None or value.strip() == "":
            missing_vars.append(var)
        else:
            env_vars[var] = value
            
    if missing_vars:
        error_message = f"Missing required environment variables: {', '.join(missing_vars)}\n"
        error_message += "Please set these variables in your .env file or environment."
        raise ConfigurationError(error_message)
        
    return env_vars

def get_redirect_uri() -> str:
    """
    Get the redirect URI from environment variables
    
    Returns:
        The redirect URI
        
    Raises:
        ConfigurationError: If the redirect URI is not set (a ValueError subclass)
    """
    redirect_uri = os.getenv("KROGER_REDIRECT_URI")
    if not redirect_uri:
        raise ConfigurationError(
            "KROGER_REDIRECT_URI environment variable is not set.\n"
            "Please set this variable in your .env file or environment."
        )
    return redirect_uri

def get_zip_code(default: str = "00000") -> str:
    """
    Get the user's zip code from environment variables
    
    Args:
        default: Default zip code to use if environment variable is not set
    
    Returns:
        The zip code from environment variable or the default
    """
    zip_code = os.getenv("KROGER_USER_ZIP_CODE")
    if not zip_code:
        logger.info("KROGER_USER_ZIP_CODE is not set; using %s", default)
        return default
    return zip_code