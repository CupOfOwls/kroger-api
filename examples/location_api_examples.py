#!/usr/bin/env python3
"""
Example script demonstrating all Location API endpoints.
"""

import os
import sys
import json

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kroger_api.kroger_api import KrogerAPI
from kroger_api.utils.env import load_and_validate_env, get_zip_code


def pretty_print(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))


def main():
    """Demonstrate all Location API endpoints"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"])
        
        # Initialize the API client
        kroger = KrogerAPI()
        
        # Authenticate with client credentials
        print("Authenticating with Kroger API...")
        token_info = kroger.authorization.get_token_with_client_credentials("product.compact")
        print(f"Authentication successful! Token expires in {token_info['expires_in']} seconds.")
        
        # Example 1: Get locations near a zip code
        print("\n============ EXAMPLE 1: SEARCH LOCATIONS BY ZIP CODE ============")
        zip_code = get_zip_code(default="10001")  # Default to Manhattan if no zip code is set
        print(f"Searching for Kroger stores near zip code {zip_code}...")
        
        try:
            locations = kroger.location.search_locations(
                zip_code=zip_code,
                radius_in_miles=10,
                limit=5
            )
            
            if locations and "data" in locations and locations["data"]:
                # Format the locations into a table
                table_data = []
                for loc in locations["data"]:
                    address = loc["address"] if "address" in loc else {}
                    address_str = f"{address.get('addressLine1', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zipCode', '')}"
                    
                    # Get store hours if available
                    hours_str = "Not available"
                    if "hours" in loc and "monday" in loc["hours"]:
                        monday = loc["hours"]["monday"]
                        if monday.get("open24", False):
                            hours_str = "Open 24 hours"
                        elif "open" in monday and "close" in monday:
                            hours_str = f"{monday['open']} - {monday['close']}"
                    
                    table_data.append([
                        loc.get("locationId", "N/A"),
                        loc.get("name", "Unknown"),
                        loc.get("chain", "N/A"),
                        address_str,
                        loc.get("phone", "N/A"),
                        hours_str
                    ])
                
                # Display the table
                headers = ["Location ID", "Name", "Chain", "Address", "Phone", "Hours (Monday)"]
                print(tabulate(table_data, headers, tablefmt="grid"))
                
                # Save the first location ID for later examples
                first_location_id = locations["data"][0]["locationId"]
            else:
                print(f"No locations found near zip code {zip_code}.")
                first_location_id = None
        except Exception as e:
            print(f"Error searching locations: {e}")
            first_location_id = None
        
        # Example 2: Get location details
        if first_location_id:
            print("\n============ EXAMPLE 2: GET LOCATION DETAILS ============")
            print(f"Getting details for location ID {first_location_id}...")
            
            try:
                location_details = kroger.location.get_location(first_location_id)
                
                if location_details and "data" in location_details:
                    loc = location_details["data"]
                    print(f"Store Name: {loc.get('name', 'Unknown')}")
                    print(f"Chain: {loc.get('chain', 'N/A')}")
                    
                    if "address" in loc:
                        addr = loc["address"]
                        print(f"Address: {addr.get('addressLine1', '')}")
                        if "addressLine2" in addr and addr["addressLine2"]:
                            print(f"         {addr.get('addressLine2', '')}")
                        print(f"         {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipCode', '')}")
                    
                    print(f"Phone: {loc.get('phone', 'N/A')}")
                    
                    if "geolocation" in loc:
                        geo = loc["geolocation"]
                        print(f"Coordinates: {geo.get('latitude', 'N/A')}, {geo.get('longitude', 'N/A')}")
                    
                    # Display departments
                    if "departments" in loc and loc["departments"]:
                        print("\nDepartments:")
                        dept_table = []
                        for dept in loc["departments"]:
                            dept_hours = "Not available"
                            if "hours" in dept and "monday" in dept["hours"]:
                                monday = dept["hours"]["monday"]
                                if monday.get("open24", False):
                                    dept_hours = "Open 24 hours"
                                elif "open" in monday and "close" in monday:
                                    dept_hours = f"{monday['open']} - {monday['close']}"
                            
                            dept_table.append([
                                dept.get("departmentId", "N/A"),
                                dept.get("name", "Unknown"),
                                dept.get("phone", "N/A"),
                                dept_hours
                            ])
                        
                        dept_headers = ["Dept ID", "Name", "Phone", "Hours (Monday)"]
                        print(tabulate(dept_table, dept_headers, tablefmt="simple"))
                else:
                    print(f"Location with ID {first_location_id} not found.")
            except Exception as e:
                print(f"Error getting location details: {e}")
        
        # Example 3: Check if a location exists
        if first_location_id:
            print("\n============ EXAMPLE 3: CHECK IF LOCATION EXISTS ============")
            print(f"Checking if location ID {first_location_id} exists...")
            
            try:
                exists = kroger.location.location_exists(first_location_id)
                print(f"Location exists: {exists}")
            except Exception as e:
                print(f"Error checking if location exists: {e}")
        else:
            print("\n============ EXAMPLE 3: CHECK IF LOCATION EXISTS ============")
            print("Skipping location existence check - no valid location ID available.")
            print("This example requires finding a location first.")
        
        # Example 4: List all chains
        print("\n============ EXAMPLE 4: LIST ALL CHAINS ============")
        print("Getting list of all Kroger-owned chains...")
        
        try:
            chains = kroger.location.list_chains()
            
            if chains and "data" in chains and chains["data"]:
                # Format the chains into a table
                chain_table = []
                for chain in chains["data"]:
                    chain_table.append([
                        chain.get("name", "Unknown"),
                        ", ".join(chain.get("divisionNumbers", []))
                    ])
                
                # Display the table
                chain_headers = ["Chain Name", "Division Numbers"]
                print(tabulate(chain_table, chain_headers, tablefmt="pretty"))
                
                # Save the first chain name for later examples
                first_chain_name = chains["data"][0]["name"]
            else:
                print("No chains found.")
                print("No chains available for further examples.")
                first_chain_name = None
        except Exception as e:
            print(f"Error listing chains: {e}")
            first_chain_name = None
        
        # Example 5: Get chain details
        if first_chain_name:
            print("\n============ EXAMPLE 5: GET CHAIN DETAILS ============")
            print(f"Getting details for chain '{first_chain_name}'...")
            
            try:
                chain_details = kroger.location.get_chain(first_chain_name)
                
                if chain_details and "data" in chain_details:
                    chain = chain_details["data"]
                    print(f"Chain Name: {chain.get('name', 'Unknown')}")
                    print(f"Division Numbers: {', '.join(chain.get('divisionNumbers', []))}")
                else:
                    print(f"Chain '{first_chain_name}' not found.")
            except Exception as e:
                print(f"Error getting chain details: {e}")
        else:
            print("\n============ EXAMPLE 5: GET CHAIN DETAILS ============")
            print("Skipping chain details - no valid chain name available.")
            print("This example requires listing chains first.")
        
        # Example 6: Check if a chain exists
        if first_chain_name:
            print("\n============ EXAMPLE 6: CHECK IF CHAIN EXISTS ============")
            print(f"Checking if chain '{first_chain_name}' exists...")
            
            try:
                chain_exists = kroger.location.chain_exists(first_chain_name)
                print(f"Chain exists: {chain_exists}")
            except Exception as e:
                print(f"Error checking if chain exists: {e}")
        else:
            print("\n============ EXAMPLE 6: CHECK IF CHAIN EXISTS ============")
            print("Skipping chain existence check - no valid chain name available.")
            print("This example requires listing chains first.")
        
        # Example 7: List all departments
        print("\n============ EXAMPLE 7: LIST ALL DEPARTMENTS ============")
        print("Getting list of all departments...")
        
        try:
            departments = kroger.location.list_departments()
            
            if departments and "data" in departments and departments["data"]:
                # Format the departments into a table
                dept_list_table = []
                for dept in departments["data"]:
                    dept_list_table.append([
                        dept.get("departmentId", "N/A"),
                        dept.get("name", "Unknown")
                    ])
                
                # Display the table
                dept_list_headers = ["Department ID", "Name"]
                print(tabulate(dept_list_table, dept_list_headers, tablefmt="pretty"))
                
                # Save the first department ID for later examples
                first_dept_id = departments["data"][0]["departmentId"]
            else:
                print("No departments found.")
                print("No departments available for further examples.")
                first_dept_id = None
        except Exception as e:
            print(f"Error listing departments: {e}")
            first_dept_id = None
        
        # Example 8: Get department details
        if first_dept_id:
            print("\n============ EXAMPLE 8: GET DEPARTMENT DETAILS ============")
            print(f"Getting details for department ID '{first_dept_id}'...")
            
            try:
                dept_details = kroger.location.get_department(first_dept_id)
                
                if dept_details and "data" in dept_details:
                    dept = dept_details["data"]
                    print(f"Department ID: {dept.get('departmentId', 'N/A')}")
                    print(f"Name: {dept.get('name', 'Unknown')}")
                else:
                    print(f"Department with ID '{first_dept_id}' not found.")
            except Exception as e:
                print(f"Error getting department details: {e}")
        else:
            print("\n============ EXAMPLE 8: GET DEPARTMENT DETAILS ============")
            print("Skipping department details - no valid department ID available.")
            print("This example requires listing departments first.")
        
        # Example 9: Check if a department exists
        if first_dept_id:
            print("\n============ EXAMPLE 9: CHECK IF DEPARTMENT EXISTS ============")
            print(f"Checking if department ID '{first_dept_id}' exists...")
            
            try:
                dept_exists = kroger.location.department_exists(first_dept_id)
                print(f"Department exists: {dept_exists}")
            except Exception as e:
                print(f"Error checking if department exists: {e}")
        else:
            print("\n============ EXAMPLE 9: CHECK IF DEPARTMENT EXISTS ============")
            print("Skipping department existence check - no valid department ID available.")
            print("This example requires listing departments first.")
            
        print("\nAll examples completed!")
        print("Token remains valid for future requests until it expires.")
        print("The improved token management system will automatically refresh tokens when needed.")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # Check if tabulate is installed
    try:
        from tabulate import tabulate
    except ImportError:
        print("The 'tabulate' package is required for this script.")
        print("Please install it with: pip install tabulate")
        sys.exit(1)
    
    main()
