from typing import Dict, List, Any

from kroger_api import validation
from kroger_api.client import KrogerClient


class CartAPI:
    """
    Provides access to the Kroger Cart API endpoints.
    """
    
    def __init__(self, client: KrogerClient):
        """
        Initialize the Cart API
        
        Args:
            client: The KrogerClient instance
        """
        self.client = client
    
    def add_to_cart(self, items: List[Dict[str, Any]]) -> None:
        """
        Add items to an authenticated customer's cart
        
        Args:
            items: A list of items to add to the cart. Each item should be a dictionary with keys:
                  - upc: The UPC of the item (13 digits)
                  - quantity: The quantity of the item (an integer of 1 or more)
                  - modality: (Optional) The modality including: DELIVERY, PICKUP
                  
        Returns:
            None if successful

        Raises:
            InvalidParameterError: If an item is malformed; no request is sent
            PermissionDeniedError: If the token is not a user token with cart.basic:write
            BadRequestError: If the API rejects an item
        """
        data = {
            "items": validation.cart_items(items)
        }
        
        return self.client._make_request('PUT', '/v1/cart/add', data=data)
