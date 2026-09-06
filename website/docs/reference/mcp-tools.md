---
sidebar_position: 1
title: kroger-mcp tool reference
description: "Every tool the kroger-mcp server exposes, grouped by family, with its purpose and whether it requires user authentication."
---

# kroger-mcp tool reference

Every tool the [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp) server exposes. **Auth Required: Yes** means the tool acts on a user's Kroger account and needs the user OAuth flow, started with `start_authentication` and finished with `complete_authentication`; **No** means it rides the client-credentials token. See [How MCP approval and scopes work](../concepts/mcp-approval.md) for what that distinction means in practice.

## Location tools

| Tool                     | Description                                     | Auth Required |
| ------------------------ | ----------------------------------------------- | ------------- |
| `search_locations`       | Find Kroger stores near a ZIP code              | No            |
| `get_location_details`   | Get detailed information about a specific store | No            |
| `set_preferred_location` | Set a preferred store for future operations     | No            |
| `get_preferred_location` | Get the currently set preferred store           | No            |
| `check_location_exists`  | Verify that a location ID is valid              | No            |
| `get_user_zip_code`      | Get the configured default ZIP code             | No            |

## Product tools

| Tool                    | Description                                                            | Auth Required |
| ----------------------- | ---------------------------------------------------------------------- | ------------- |
| `search_products`       | Search for products by name, brand, or other criteria                  | No            |
| `bulk_search_products`  | Run up to 25 product searches in a single call                         | No            |
| `get_product_details`   | Get detailed product information including pricing                     | No            |
| `search_products_by_id` | Find products by their specific product ID                             | No            |
| `get_product_images`    | Get a product image from a chosen perspective (front, back, and so on) | No            |

## Cart tools

| Tool                 | Description                                     | Auth Required |
| -------------------- | ----------------------------------------------- | ------------- |
| `add_items_to_cart`  | Add a single item to the cart                   | Yes           |
| `bulk_add_to_cart`   | Add multiple items to the cart in one operation | Yes           |
| `view_current_cart`  | View items in the local cart tracking           | No            |
| `remove_from_cart`   | Remove items from local cart tracking           | No            |
| `clear_current_cart` | Clear all items from local cart tracking        | No            |
| `mark_order_placed`  | Move the current cart to order history          | No            |
| `view_order_history` | View the history of placed orders               | No            |

The Kroger Public API does not offer cart _viewing_, so the server keeps a local record (`kroger_cart.json`, `kroger_order_history.json`) alongside the real account writes. The local record is the agent's memory of intent; the account is the source of truth.

## Information tools

| Tool                      | Description                             | Auth Required |
| ------------------------- | --------------------------------------- | ------------- |
| `list_chains`             | Get all Kroger-owned chains             | No            |
| `get_chain_details`       | Get details about a specific chain      | No            |
| `check_chain_exists`      | Check whether a chain exists            | No            |
| `list_departments`        | Get all store departments               | No            |
| `get_department_details`  | Get details about a specific department | No            |
| `check_department_exists` | Check whether a department exists       | No            |

## Profile tools

| Tool                      | Description                                      | Auth Required |
| ------------------------- | ------------------------------------------------ | ------------- |
| `get_user_profile`        | Get the authenticated user's profile information | Yes           |
| `test_authentication`     | Test whether the authentication token is valid   | Yes           |
| `get_authentication_info` | Get detailed authentication status               | Yes           |
| `force_reauthenticate`    | Clear tokens and force re-authentication         | No            |

## Authentication tools

| Tool                      | Description                                                      | Auth Required |
| ------------------------- | ---------------------------------------------------------------- | ------------- |
| `start_authentication`    | Begin the user OAuth flow; returns a sign-in URL for you to open | No            |
| `complete_authentication` | Finish the flow with the redirect URL you paste back             | No            |

## Utility tools

| Tool                   | Description                          | Auth Required |
| ---------------------- | ------------------------------------ | ------------- |
| `get_current_datetime` | Get the current system date and time | No            |
