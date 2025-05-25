from typing import Dict, Any

from kroger_api.client import KrogerClient


class IdentityAPI:
    """
    Provides access to the Kroger Identity API endpoints.
    """
    
    def __init__(self, client: KrogerClient):
        """
        Initialize the Identity API
        
        Args:
            client: The KrogerClient instance
        """
        self.client = client
    
    def get_profile(self) -> Dict[str, Any]:
        """
        Get the profile ID of an authenticated customer
        
        Returns:
            The user profile information
        """
        return self.client._make_request('GET', '/v1/identity/profile')
