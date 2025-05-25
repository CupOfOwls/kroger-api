from typing import Dict, Optional, Any, List, Union

from kroger_api.client import KrogerClient


class ProductAPI:
    """
    Provides access to the Kroger Product API endpoints.
    """
    
    def __init__(self, client: KrogerClient):
        """
        Initialize the Product API
        
        Args:
            client: The KrogerClient instance
        """
        self.client = client
    
    def search_products(self, 
                        term: Optional[str] = None, 
                        location_id: Optional[str] = None,
                        product_id: Optional[str] = None,
                        brand: Optional[str] = None,
                        fulfillment: Optional[str] = None,
                        start: Optional[int] = None,
                        limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Search for products
        
        Args:
            term: A search term to filter product results
            location_id: The locationId of the location
            product_id: The productId of the products(s) to return (comma-separated)
            brand: The brand name of the products to return (pipe-separated)
            fulfillment: The available fulfillment types (comma-separated)
            start: The number of products to skip
            limit: The number of products to return
            
        Returns:
            The products matching the search criteria
        """
        params = {}
        
        if term:
            params['filter.term'] = term
        
        if location_id:
            params['filter.locationId'] = location_id
        
        if product_id:
            params['filter.productId'] = product_id
        
        if brand:
            params['filter.brand'] = brand
        
        if fulfillment:
            params['filter.fulfillment'] = fulfillment
        
        if start:
            params['filter.start'] = start
        
        if limit:
            params['filter.limit'] = limit
        
        return self.client._make_request('GET', '/v1/products', params=params)
    
    def get_product(self, product_id: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details for a specific product
        
        Args:
            product_id: The productId of the product
            location_id: The locationId of the location for pricing and availability
            
        Returns:
            The product details
        """
        params = {}
        
        if location_id:
            params['filter.locationId'] = location_id
        
        return self.client._make_request('GET', f'/v1/products/{product_id}', params=params)
