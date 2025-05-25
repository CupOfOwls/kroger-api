from typing import Dict, List, Any

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
                  - upc: The UPC of the item
                  - quantity: The quantity of the item
                  - modality: (Optional) The modality including: DELIVERY, PICKUP
                  
        Returns:
            None if successful
        """
        data = {
            "items": items
        }
        
        return self.client._make_request('PUT', '/v1/cart/add', data=data)
