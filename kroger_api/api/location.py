from typing import Dict, Optional, Any, List, Union
from urllib.parse import quote

from kroger_api import validation
from kroger_api.client import KrogerClient
from kroger_api.errors import NotFoundError


class LocationAPI:
    """
    Provides access to the Kroger Location API endpoints.
    """
    
    def __init__(self, client: KrogerClient):
        """
        Initialize the Location API
        
        Args:
            client: The KrogerClient instance
        """
        self.client = client
    
    def search_locations(self, 
                         zip_code: Optional[str] = None,
                         lat_long: Optional[str] = None,
                         lat: Optional[str] = None,
                         lon: Optional[str] = None,
                         radius_in_miles: Optional[int] = None,
                         limit: Optional[int] = None,
                         chain: Optional[str] = None,
                         department: Optional[str] = None,
                         location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for locations
        
        Args:
            zip_code: The zip code to use as a starting point for results (5 digits)
            lat_long: The latitude and longitude to use as a starting point for results (comma separated)
            lat: The latitude to use as a starting point for results
            lon: The longitude to use as a starting point for results
            radius_in_miles: The mile radius of results (1-100)
            limit: The number of results to return (1-200)
            chain: The chain name
            department: The departmentId of the department (2 characters each, comma separated)
            location_id: Comma-separated list of locationIds (8 characters each)
            
        Returns:
            The locations matching the search criteria

        Raises:
            InvalidParameterError: If a parameter is invalid; no request is sent
            APIStatusError: If the API rejects the request
        """
        params = {}
        
        if zip_code is not None:
            params['filter.zipCode.near'] = validation.zip_code(zip_code)
        
        if lat_long is not None:
            params['filter.latLong.near'] = validation.lat_long(lat_long)
        
        if lat is not None:
            params['filter.lat.near'] = validation.coordinate(lat, "lat", 90)
        
        if lon is not None:
            params['filter.lon.near'] = validation.coordinate(lon, "lon", 180)
        
        if radius_in_miles is not None:
            params['filter.radiusInMiles'] = validation.check_int(
                "radius_in_miles", radius_in_miles, validation.LOCATION_RADIUS_MIN, validation.LOCATION_RADIUS_MAX)
        
        if limit is not None:
            params['filter.limit'] = validation.check_int(
                "limit", limit, validation.LOCATION_LIMIT_MIN, validation.LOCATION_LIMIT_MAX)
        
        if chain is not None:
            params['filter.chain'] = validation.check_non_empty("chain", chain)
        
        if department is not None:
            params['filter.department'] = validation.department_id_list(department)
        
        if location_id is not None:
            params['filter.locationId'] = validation.location_id_list(location_id)
        
        return self.client._make_request('GET', '/v1/locations', params=params)
    
    def get_location(self, location_id: str) -> Dict[str, Any]:
        """
        Get details for a specific location
        
        Args:
            location_id: The locationId of the store (8 characters)
            
        Returns:
            The location details

        Raises:
            InvalidParameterError: If location_id is malformed; no request is sent
            NotFoundError: If no store has this locationId
        """
        location_id = validation.location_id(location_id)
        return self.client._make_request('GET', f'/v1/locations/{quote(location_id, safe="")}')
    
    def location_exists(self, location_id: str) -> bool:
        """
        Check if a location exists
        
        Args:
            location_id: The locationId of the store (8 characters)
            
        Returns:
            True if the location exists, False otherwise

        Raises:
            InvalidParameterError: If location_id is malformed; no request is sent
        """
        location_id = validation.location_id(location_id)
        try:
            self.client._make_request('HEAD', f'/v1/locations/{quote(location_id, safe="")}')
            return True
        except NotFoundError:
            return False
    
    def list_chains(self) -> Dict[str, Any]:
        """
        Get a list of all chains
        
        Returns:
            A list of all chains
        """
        return self.client._make_request('GET', '/v1/chains')
    
    def get_chain(self, name: str) -> Dict[str, Any]:
        """
        Get details for a specific chain
        
        Args:
            name: The name of the chain (case-insensitive; may contain spaces, such as "FRED MEYER STORES")
            
        Returns:
            The chain details

        Raises:
            InvalidParameterError: If name is empty; no request is sent
            NotFoundError: If no chain has this name
        """
        name = validation.check_non_empty("name", name)
        return self.client._make_request('GET', f'/v1/chains/{quote(name, safe="")}')
    
    def chain_exists(self, name: str) -> bool:
        """
        Check if a chain exists
        
        Args:
            name: The name of the chain
            
        Returns:
            True if the chain exists, False otherwise

        Raises:
            InvalidParameterError: If name is empty; no request is sent
        """
        name = validation.check_non_empty("name", name)
        try:
            self.client._make_request('HEAD', f'/v1/chains/{quote(name, safe="")}')
            return True
        except NotFoundError:
            return False
    
    def list_departments(self) -> Dict[str, Any]:
        """
        Get a list of all departments
        
        Returns:
            A list of all departments
        """
        return self.client._make_request('GET', '/v1/departments')
    
    def get_department(self, department_id: str) -> Dict[str, Any]:
        """
        Get details for a specific department
        
        Args:
            department_id: The departmentId of the department (2 characters)
            
        Returns:
            The department details

        Raises:
            InvalidParameterError: If department_id is malformed; no request is sent
            NotFoundError: If no department has this ID
        """
        department_id = validation.department_id(department_id)
        return self.client._make_request('GET', f'/v1/departments/{quote(department_id, safe="")}')
    
    def department_exists(self, department_id: str) -> bool:
        """
        Check if a department exists
        
        Args:
            department_id: The departmentId of the department (2 characters)
            
        Returns:
            True if the department exists, False otherwise

        Raises:
            InvalidParameterError: If department_id is malformed; no request is sent
        """
        department_id = validation.department_id(department_id)
        try:
            self.client._make_request('HEAD', f'/v1/departments/{quote(department_id, safe="")}')
            return True
        except NotFoundError:
            return False
