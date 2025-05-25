from typing import Dict, Optional, Any, List, Union
import requests

from kroger_api.client import KrogerClient


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
            zip_code: The zip code to use as a starting point for results
            lat_long: The latitude and longitude to use as a starting point for results (comma separated)
            lat: The latitude to use as a starting point for results
            lon: The longitude to use as a starting point for results
            radius_in_miles: The mile radius of results (1-100)
            limit: The number of results to return (1-200)
            chain: The chain name
            department: The departmentId of the department (comma separated)
            location_id: Comma-separated list of locationIds
            
        Returns:
            The locations matching the search criteria
        """
        params = {}
        
        if zip_code:
            params['filter.zipCode.near'] = zip_code
        
        if lat_long:
            params['filter.latLong.near'] = lat_long
        
        if lat:
            params['filter.lat.near'] = lat
        
        if lon:
            params['filter.lon.near'] = lon
        
        if radius_in_miles:
            params['filter.radiusInMiles'] = radius_in_miles
        
        if limit:
            params['filter.limit'] = limit
        
        if chain:
            params['filter.chain'] = chain
        
        if department:
            params['filter.department'] = department
        
        if location_id:
            params['filter.locationId'] = location_id
        
        return self.client._make_request('GET', '/v1/locations', params=params)
    
    def get_location(self, location_id: str) -> Dict[str, Any]:
        """
        Get details for a specific location
        
        Args:
            location_id: The locationId of the store
            
        Returns:
            The location details
        """
        return self.client._make_request('GET', f'/v1/locations/{location_id}')
    
    def location_exists(self, location_id: str) -> bool:
        """
        Check if a location exists
        
        Args:
            location_id: The locationId of the store
            
        Returns:
            True if the location exists, False otherwise
        """
        try:
            self.client._make_request('HEAD', f'/v1/locations/{location_id}')
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise
    
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
            name: The name of the chain
            
        Returns:
            The chain details
        """
        return self.client._make_request('GET', f'/v1/chains/{name}')
    
    def chain_exists(self, name: str) -> bool:
        """
        Check if a chain exists
        
        Args:
            name: The name of the chain
            
        Returns:
            True if the chain exists, False otherwise
        """
        try:
            self.client._make_request('HEAD', f'/v1/chains/{name}')
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise
    
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
            department_id: The departmentId of the department
            
        Returns:
            The department details
        """
        return self.client._make_request('GET', f'/v1/departments/{department_id}')
    
    def department_exists(self, department_id: str) -> bool:
        """
        Check if a department exists
        
        Args:
            department_id: The departmentId of the department
            
        Returns:
            True if the department exists, False otherwise
        """
        try:
            self.client._make_request('HEAD', f'/v1/departments/{department_id}')
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise
