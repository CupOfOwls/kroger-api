from kroger_api.client import KrogerClient
from kroger_api.api.authorization import AuthorizationAPI
from kroger_api.api.location import LocationAPI
from kroger_api.api.product import ProductAPI
from kroger_api.api.cart import CartAPI
from kroger_api.api.identity import IdentityAPI


class KrogerAPI:
    """
    Main class for interacting with the Kroger API
    """
    
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        """
        Initialize the Kroger API
        
        Args:
            client_id: Your Kroger API client ID
            client_secret: Your Kroger API client secret
            redirect_uri: The redirect URI registered with your Kroger API application
        """
        self.client = KrogerClient(client_id, client_secret, redirect_uri)
        
        # Initialize API modules
        self.authorization = AuthorizationAPI(self.client)
        self.location = LocationAPI(self.client)
        self.product = ProductAPI(self.client)
        self.cart = CartAPI(self.client)
        self.identity = IdentityAPI(self.client)
    
    def test_current_token(self):
        """
        Test if the current token is valid
        
        Returns:
            True if the token is valid, False otherwise
        """
        if self.client.token_info:
            return self.client.test_token(self.client.token_info)
        return False
