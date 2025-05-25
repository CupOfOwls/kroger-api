#!/usr/bin/env python3
"""
Example script demonstrating all Product API endpoints.
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


def format_currency(value):
    """Format a value as currency"""
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def main():
    """Demonstrate all Product API endpoints"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"])
        
        # Initialize the API client
        kroger = KrogerAPI()
        
        # Authenticate with client credentials
        print("Authenticating with Kroger API...")
        token_info = kroger.authorization.get_token_with_client_credentials("product.compact")
        print(f"Authentication successful! Token expires in {token_info['expires_in']} seconds.")
        
        # Find a location to use for product searches
        print("\nFinding a Kroger store location...")
        try:
            # Get zip code from environment variable
            zip_code = get_zip_code(default="10001")  # Default to Manhattan if not set
            
            locations = kroger.location.search_locations(
                zip_code=zip_code,
                radius_in_miles=10,
                limit=1
            )
            
            if not locations or "data" not in locations or not locations["data"]:
                print(f"No locations found near zip code {zip_code}. Cannot proceed with product searches.")
                print("Please check your zip code in the .env file or try a different zip code.")
                return
            else:
                location_id = locations["data"][0]["locationId"]
                print(f"Using store: {locations['data'][0]['name']} (ID: {location_id})")
        except Exception as e:
            print(f"Error finding location: {e}")
            print("Cannot proceed without a valid location. Please check your environment setup.")
            return
        
        # Example 1: Search for products by term
        print("\n============ EXAMPLE 1: SEARCH PRODUCTS BY TERM ============")
        search_term = "milk"
        print(f"Searching for products with term '{search_term}'...")
        
        try:
            products = kroger.product.search_products(
                term=search_term,
                location_id=location_id,
                limit=5
            )
            
            if products and "data" in products and products["data"]:
                # Format the products into a table
                table_data = []
                for product in products["data"]:
                    # Extract price information if available
                    price = "N/A"
                    promo_price = "N/A"
                    if "items" in product and product["items"]:
                        item = product["items"][0]
                        if "price" in item:
                            price = format_currency(item["price"].get("regular"))
                            promo_price = format_currency(item["price"].get("promo"))
                    
                    # Extract size information
                    size = "N/A"
                    if "items" in product and product["items"]:
                        size = product["items"][0].get("size", "N/A")
                    
                    # Add to table
                    table_data.append([
                        product.get("productId", "N/A"),
                        product.get("description", "Unknown"),
                        product.get("brand", "N/A"),
                        size,
                        price,
                        promo_price
                    ])
                
                # Display the table
                headers = ["Product ID", "Description", "Brand", "Size", "Regular Price", "Sale Price"]
                print(tabulate(table_data, headers, tablefmt="grid"))
                
                # Save the first product ID for later examples
                first_product_id = products["data"][0]["productId"]
            else:
                print(f"No products found matching term '{search_term}'.")
                first_product_id = "0001111041700"  # A common Kroger milk product ID
        except Exception as e:
            print(f"Error searching products: {e}")
            first_product_id = "0001111041700"  # A common Kroger milk product ID
        
        # Example 3: Get product details
        print("\n============ EXAMPLE 3: GET PRODUCT DETAILS ============")
        print(f"Getting details for product ID {first_product_id}...")
        
        try:
            product_details = kroger.product.get_product(
                product_id=first_product_id,
                location_id=location_id
            )
            
            if product_details and "data" in product_details:
                product = product_details["data"]
                
                print(f"Product ID: {product.get('productId', 'N/A')}")
                print(f"UPC: {product.get('upc', 'N/A')}")
                print(f"Description: {product.get('description', 'Unknown')}")
                print(f"Brand: {product.get('brand', 'N/A')}")
                
                # Display categories
                if "categories" in product and product["categories"]:
                    print(f"Categories: {', '.join(product['categories'])}")
                
                # Display country of origin if available
                if "countryOrigin" in product:
                    print(f"Country of Origin: {product['countryOrigin']}")
                
                # Display temperature info if available
                if "temperature" in product:
                    temp = product["temperature"]
                    print(f"Temperature: {temp.get('indicator', 'N/A')}")
                    if "heatSensitive" in temp:
                        print(f"Heat Sensitive: {temp['heatSensitive']}")
                
                # Display item info
                if "items" in product and product["items"]:
                    item = product["items"][0]
                    print("\nItem Information:")
                    print(f"  Size: {item.get('size', 'N/A')}")
                    print(f"  Sold By: {item.get('soldBy', 'N/A')}")
                    
                    # Display inventory if available
                    if "inventory" in item:
                        print(f"  Stock Level: {item['inventory'].get('stockLevel', 'N/A')}")
                    
                    # Display fulfillment options if available
                    if "fulfillment" in item:
                        fulfill = item["fulfillment"]
                        print("\nFulfillment Options:")
                        print(f"  In Store: {fulfill.get('instore', False)}")
                        print(f"  Curbside Pickup: {fulfill.get('curbside', False)}")
                        print(f"  Delivery: {fulfill.get('delivery', False)}")
                        print(f"  Ship to Home: {fulfill.get('shiptohome', False)}")
                    
                    # Display pricing information if available
                    if "price" in item:
                        price = item["price"]
                        print("\nPricing:")
                        print(f"  Regular Price: {format_currency(price.get('regular', None))}")
                        if "promo" in price and price["promo"] is not None:
                            print(f"  Sale Price: {format_currency(price['promo'])}")
                        if "regularPerUnitEstimate" in price:
                            print(f"  Regular Price Per Unit: {format_currency(price['regularPerUnitEstimate'])}")
                
                # Display aisle locations if available
                if "aisleLocations" in product and product["aisleLocations"]:
                    print("\nAisle Locations:")
                    for aisle in product["aisleLocations"]:
                        print(f"  {aisle.get('description', 'N/A')}")
                        if "number" in aisle:
                            print(f"  Aisle Number: {aisle['number']}")
                        if "side" in aisle:
                            print(f"  Side: {aisle['side']}")
                        if "shelfNumber" in aisle:
                            print(f"  Shelf: {aisle['shelfNumber']}")
                        print()
                
                # Display images if available
                if "images" in product and product["images"]:
                    print("\nImages:")
                    for img in product["images"]:
                        perspective = img.get("perspective", "N/A")
                        if "sizes" in img and img["sizes"]:
                            size = img["sizes"][0]
                            if "size" in size and "url" in size:
                                print(f"  {perspective} ({size['size']}): {size['url']}")
            else:
                print(f"Product with ID {first_product_id} not found.")
        except Exception as e:
            print(f"Error getting product details: {e}")
        
        # Example 4: Search for products by product ID
        print("\n============ EXAMPLE 4: SEARCH PRODUCTS BY PRODUCT ID ============")
        print(f"Searching for products with ID '{first_product_id}'...")
        
        try:
            id_products = kroger.product.search_products(
                product_id=first_product_id,
                location_id=location_id
            )
            
            if id_products and "data" in id_products and id_products["data"]:
                print(f"Found {len(id_products['data'])} product(s) with ID '{first_product_id}'")
                product = id_products["data"][0]
                print(f"Product: {product.get('description', 'Unknown')} - {product.get('brand', 'N/A')}")
            else:
                print(f"No products found with ID '{first_product_id}'.")
        except Exception as e:
            print(f"Error searching products by ID: {e}")
        
        # Example 5: Search for products with fulfillment options
        print("\n============ EXAMPLE 5: SEARCH PRODUCTS BY FULFILLMENT ============")
        fulfillment = "csp"  # Curbside Pickup
        print(f"Searching for products with fulfillment option '{fulfillment}'...")
        
        try:
            fulfill_products = kroger.product.search_products(
                term="bread",
                location_id=location_id,
                fulfillment=fulfillment,
                limit=5
            )
            
            if fulfill_products and "data" in fulfill_products and fulfill_products["data"]:
                print(f"Found {len(fulfill_products['data'])} product(s) with fulfillment option '{fulfillment}'")
                
                # Format the products into a table
                fulfill_table_data = []
                for product in fulfill_products["data"]:
                    # Add to table
                    fulfill_table_data.append([
                        product.get("productId", "N/A"),
                        product.get("description", "Unknown"),
                        product.get("brand", "N/A")
                    ])
                
                # Display the table
                fulfill_headers = ["Product ID", "Description", "Brand"]
                print(tabulate(fulfill_table_data, fulfill_headers, tablefmt="simple"))
            else:
                print(f"No products found with fulfillment option '{fulfillment}'.")
        except Exception as e:
            print(f"Error searching products by fulfillment: {e}")
            
        print("\nAll examples completed!")
        print("Token remains valid for future requests until it expires.")
        print("The token management system will automatically refresh tokens when needed.")
    
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
