#!/usr/bin/env python3
"""
Example script demonstrating the Cart API endpoint.
This requires the OAuth2 authorization flow with user interaction.
"""

import os
import sys
import json

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kroger_api.kroger_api import KrogerAPI
from kroger_api.auth import authenticate_user, switch_to_client_credentials
from kroger_api.utils.env import load_and_validate_env, get_zip_code


def pretty_print(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2))


def main():
    """Demonstrate the Cart API endpoint"""
    try:
        # Load and validate environment variables
        load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET", "KROGER_REDIRECT_URI"])
        
        # Authenticate and get the Kroger client
        print("Authenticating with Kroger...")
        kroger = authenticate_user(scopes="cart.basic:write profile.compact")
        
        # Find a store near a zip code
        print("\nFinding a Kroger store location...")
        
        # Switch to client credentials for the location and product API
        # Save the user's token for later restoration
        print("Switching to client credentials for product and location APIs...")
        kroger, user_token_info, user_token_file = switch_to_client_credentials(kroger, scope="product.compact")
        
        # Get zip code from environment variable
        zip_code = get_zip_code(default="10001")  # Default to Manhattan if not set
        
        # Find stores near the zip code
        print(f"Searching for stores near zip code {zip_code}...")
        locations = kroger.location.search_locations(
            zip_code=zip_code,
            radius_in_miles=10,
            limit=5
        )
        
        if not locations or "data" not in locations or not locations["data"]:
            print("No stores found. Please try a different zip code.")
            return
        
        # Display stores and let user choose one
        print("\nNearby Kroger stores:")
        for i, loc in enumerate(locations["data"]):
            print(f"{i+1}. {loc['name']} - {loc['address']['addressLine1']}, {loc['address']['city']}, {loc['address']['state']}")
        
        choice = 0
        while choice < 1 or choice > len(locations["data"]):
            try:
                choice = int(input(f"\nSelect a store (1-{len(locations['data'])}): "))
            except ValueError:
                print("Please enter a valid number.")
        
        location_id = locations["data"][choice-1]["locationId"]
        store_name = locations["data"][choice-1]["name"]
        print(f"\nSelected store: {store_name} (ID: {location_id})")
        
        # Search for products to add to the cart
        print("\nSearching for products...")
        
        search_term = input("\nEnter a product to search for (e.g., milk, bread, eggs): ")
        
        products = kroger.product.search_products(
            term=search_term,
            location_id=location_id,
            limit=5
        )
        
        if not products or "data" not in products or not products["data"]:
            print(f"No products found matching '{search_term}'. Please try a different search term.")
            return
        
        # Display products and let user choose one
        print("\nProducts found:")
        for i, product in enumerate(products["data"]):
            description = product.get("description", "Unknown")
            brand = product.get("brand", "N/A")
            
            # Get price if available
            price_str = "Price not available"
            if "items" in product and product["items"] and "price" in product["items"][0]:
                price = product["items"][0]["price"]
                if "regular" in price:
                    price_str = f"${price['regular']:.2f}"
                    if "promo" in price and price["promo"]:
                        price_str += f" (Sale: ${price['promo']:.2f})"
            
            # Get size if available
            size = ""
            if "items" in product and product["items"] and "size" in product["items"][0]:
                size = product["items"][0]["size"]
                if size:
                    size = f" - {size}"
            
            print(f"{i+1}. {description} - {brand}{size} - {price_str}")
        
        product_choice = 0
        while product_choice < 1 or product_choice > len(products["data"]):
            try:
                product_choice = int(input(f"\nSelect a product to add to your cart (1-{len(products['data'])}): "))
            except ValueError:
                print("Please enter a valid number.")
        
        selected_product = products["data"][product_choice-1]
        product_id = selected_product["productId"]
        product_name = selected_product.get("description", "Unknown")
        
        # Ask for quantity
        quantity = 0
        while quantity < 1:
            try:
                quantity = int(input("\nEnter quantity (1 or more): "))
            except ValueError:
                print("Please enter a valid number.")
        
        # Ask for modality
        print("\nSelect delivery method:")
        print("1. Pickup at store")
        print("2. Home delivery")
        
        modality_choice = 0
        while modality_choice < 1 or modality_choice > 2:
            try:
                modality_choice = int(input("\nEnter choice (1-2): "))
            except ValueError:
                print("Please enter a valid number.")
        
        modality = "PICKUP" if modality_choice == 1 else "DELIVERY"
        
        # Example 1: Add to cart
        print("\n============ EXAMPLE 1: ADD TO CART ============")
        print(f"Adding {quantity} x {product_name} to your cart...")
        
        # Restore the user's token for cart operations
        print("Restoring user token for cart operations...")
        if user_token_info:
            kroger.client.token_info = user_token_info
        if user_token_file:
            kroger.client.token_file = user_token_file
        
        try:
            # Add the item to the cart
            kroger.cart.add_to_cart([
                {
                    "upc": product_id,
                    "quantity": quantity,
                    "modality": modality
                }
            ])
            
            print("\nItem successfully added to your cart!")
            print(f"\nProduct: {product_name}")
            print(f"Quantity: {quantity}")
            print(f"Modality: {modality}")
            print("\nYou can now go to the Kroger website or app to complete your order.")
        
        except Exception as e:
            print(f"\nError adding item to cart: {e}")
            print("Please try again or check your authorization.")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
