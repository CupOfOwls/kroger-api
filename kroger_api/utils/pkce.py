"""
PKCE (Proof Key for Code Exchange) utilities for secure OAuth2 authorization code flow
"""
import base64
import hashlib
import secrets
from typing import Dict, Any

def generate_code_verifier(length: int = 64) -> str:
    """
    Generate a random code verifier for PKCE
    
    Args:
        length: Length of the code verifier (default: 64)
        
    Returns:
        A random code verifier string
    """
    return secrets.token_urlsafe(length)

def generate_code_challenge(code_verifier: str, method: str = 'S256') -> str:
    """
    Generate a code challenge from the code verifier
    
    Args:
        code_verifier: The code verifier to generate the challenge from
        method: The method to use for generating the challenge (S256 or plain)
        
    Returns:
        The code challenge
        
    Raises:
        ValueError: If the method is not supported
    """
    if method == 'S256':
        # SHA-256 transformation
        code_verifier_bytes = code_verifier.encode('ascii')
        code_challenge_bytes = hashlib.sha256(code_verifier_bytes).digest()
        return base64.urlsafe_b64encode(code_challenge_bytes).decode('ascii').rstrip('=')
    elif method == 'plain':
        # Identity transformation
        return code_verifier
    else:
        raise ValueError(f"Unsupported code challenge method: {method}")

def generate_pkce_parameters(length: int = 64, method: str = 'S256') -> Dict[str, Any]:
    """
    Generate PKCE parameters for OAuth2 authorization code flow
    
    Args:
        length: Length of the code verifier (default: 64)
        method: The method to use for generating the challenge (S256 or plain)
        
    Returns:
        Dictionary containing code_verifier, code_challenge, and code_challenge_method
    """
    code_verifier = generate_code_verifier(length)
    code_challenge = generate_code_challenge(code_verifier, method)
    
    return {
        'code_verifier': code_verifier,
        'code_challenge': code_challenge,
        'code_challenge_method': method
    }
