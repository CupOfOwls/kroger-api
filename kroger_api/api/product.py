from typing import Dict, Optional, Any
from urllib.parse import quote

from kroger_api import validation
from kroger_api.client import KrogerClient
from kroger_api.errors import InvalidParameterError


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
            term: A search term to filter product results (at least 3 characters, at most 8 words)
            location_id: The locationId of the location (8 characters)
            product_id: The productId of the products(s) to return (13 digits each, comma-separated)
            brand: The brand name of the products to return (case-sensitive, pipe-separated)
            fulfillment: The available fulfillment types (comma-separated, case-sensitive):
                ais (available in store), csp (curbside pickup), dth (delivery to home),
                sth (ship to home)
            start: The number of products to skip (0-250)
            limit: The number of products to return (1-50)
            
        Returns:
            The products matching the search criteria

        Raises:
            InvalidParameterError: If a parameter is invalid; no request is sent
            APIStatusError: If the API rejects the request
        """
        # The Products spec also lists filter.brand as a starting value, but
        # the API rejects a brand-only search with 400 PRODUCT-2016 "Field
        # 'term' or 'productId' must be used" (checked live on 2026-10-21).
        if term is None and product_id is None:
            raise InvalidParameterError(
                "term", None, "a product search needs a term or a product_id; brand alone is not enough"
            )

        params = {}
        
        if term is not None:
            params['filter.term'] = validation.search_term(term)
        
        if location_id is not None:
            params['filter.locationId'] = validation.location_id(location_id)
        
        if product_id is not None:
            params['filter.productId'] = validation.product_id_list(product_id)
        
        if brand is not None:
            params['filter.brand'] = validation.check_non_empty("brand", brand)
        
        if fulfillment is not None:
            params['filter.fulfillment'] = validation.fulfillment(fulfillment)
        
        if start is not None:
            params['filter.start'] = validation.check_int(
                "start", start, validation.PRODUCT_START_MIN, validation.PRODUCT_START_MAX)
        
        if limit is not None:
            params['filter.limit'] = validation.check_int(
                "limit", limit, validation.PRODUCT_LIMIT_MIN, validation.PRODUCT_LIMIT_MAX)
        
        return self.client._make_request('GET', '/v1/products', params=params)
    
    def get_product(self, product_id: str, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details for a specific product
        
        Args:
            product_id: The productId or UPC of the product (13 digits)
            location_id: The locationId of the location for pricing and availability
            
        Returns:
            The product details

        Raises:
            InvalidParameterError: If a parameter is invalid; no request is sent
            APIStatusError: If the API rejects the request
        """
        product_id = validation.product_id(product_id)
        params = {}
        
        if location_id is not None:
            params['filter.locationId'] = validation.location_id(location_id)
        
        return self.client._make_request('GET', f'/v1/products/{quote(product_id, safe="")}', params=params)
