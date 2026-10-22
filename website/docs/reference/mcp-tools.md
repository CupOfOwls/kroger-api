---
sidebar_position: 1
title: kroger-mcp tool reference
description: "Every tool the kroger-mcp server exposes, grouped by family, with whether it requires user authentication, the valid parameter values, and the error results tools return."
---

# kroger-mcp tool reference

Every tool the [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp) server exposes. **Auth Required: Yes** means the tool acts on a user's Kroger account and needs the user OAuth flow, started with `start_authentication` and finished with `complete_authentication`; **No** means it rides the client-credentials token. See [How MCP approval and scopes work](../concepts/mcp-approval.md) for what that distinction means in practice. A tool that fails returns an [error result](#error-results), and each tool's input schema declares the [valid parameter values](#parameter-values).

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

| Tool                    | Description                                                                   | Auth Required |
| ----------------------- | ----------------------------------------------------------------------------- | ------------- |
| `search_products`       | Search for products by name, brand, or other criteria                         | No            |
| `bulk_search_products`  | Run up to 25 product searches in a single call                                | No            |
| `get_product_details`   | Get one product with the same fields as a search result, and every image size | No            |
| `search_products_by_id` | Find products by their specific product ID                                    | No            |
| `get_product_images`    | Get a product image from a chosen perspective (front, back, and so on)        | No            |

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

| Tool                      | Description                                                                             | Auth Required |
| ------------------------- | --------------------------------------------------------------------------------------- | ------------- |
| `get_user_profile`        | Get the authenticated user's profile information                                        | Yes           |
| `test_authentication`     | Check that the user is signed in and the token has not expired, refreshing it if it has | No            |
| `get_authentication_info` | Get detailed authentication status                                                      | No            |
| `force_reauthenticate`    | Delete the saved sign-in, so the user can sign in again                                 | No            |

`test_authentication` and `get_authentication_info` report a user who is not signed in as a normal result, not an error. `test_authentication` compares the token's expiry time with the clock and sends no request, so a sign-in that Kroger revoked early still reports `token_valid: true` until a cart call fails. `get_user_profile` needs a sign-in that grants the `profile.compact` scope. `start_authentication` requests it, together with `product.compact` and `cart.basic:write`. Sign-ins made with `kroger-mcp` before version 0.4.0 lack it, so `get_user_profile` returns a `permission_denied` error until the user signs in again; the cart tools keep working.

## Authentication tools

| Tool                      | Description                                                      | Auth Required |
| ------------------------- | ---------------------------------------------------------------- | ------------- |
| `start_authentication`    | Begin the user OAuth flow; returns a sign-in URL for you to open | No            |
| `complete_authentication` | Finish the flow with the redirect URL you paste back             | No            |

## Utility tools

| Tool                   | Description                          | Auth Required |
| ---------------------- | ------------------------------------ | ------------- |
| `get_current_datetime` | Get the current system date and time | No            |

## Parameter values

Each tool's input schema declares the values the Kroger API accepts, so an MCP client can show them to the model. A call with an invalid value fails before the server sends any request.

| Parameter                        | Tools                                               | Valid values                                                                                         |
| -------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `location_id`                    | Location and product tools                          | Eight letters or digits, such as `01400513`. Product tools default to the preferred location.        |
| `product_id`                     | Product tools, `add_items_to_cart`                  | 13 digits, such as `0001111041700`                                                                   |
| `product_id`                     | `remove_from_cart`                                  | The product ID of an item in the local cart tracking                                                 |
| `search_term`, `searches[].term` | `search_products`, `bulk_search_products`           | At least three characters and at most eight words, separated by single spaces                        |
| `limit`                          | `search_products`, `bulk_search_products`           | 1 to 50, default 10                                                                                  |
| `fulfillment`                    | `search_products`, `bulk_search_products`           | `ais` (in store), `csp` (curbside pickup), `dth` (delivery to home), or `sth` (ship to home)         |
| `brand`                          | `search_products`, `bulk_search_products`           | A brand name, case-sensitive, such as `Kroger`. Not only spaces.                                     |
| `searches`                       | `bulk_search_products`                              | 1 to 25 searches. Each takes `term`, `limit`, `fulfillment`, and `brand`, and no other keys.         |
| `zip_code`                       | `search_locations`                                  | Five digits. ZIP+4 is not accepted. Defaults to `KROGER_USER_ZIP_CODE`, or `10001` if it is not set. |
| `radius_in_miles`                | `search_locations`                                  | 1 to 100, default 10                                                                                 |
| `limit`                          | `search_locations`                                  | 1 to 200, default 10                                                                                 |
| `chain_name`                     | `get_chain_details`, `check_chain_exists`           | A chain name from `list_chains`, such as `LOAF 'N JUG`                                               |
| `department_id`                  | `get_department_details`, `check_department_exists` | Two letters or digits, from `list_departments`                                                       |
| `quantity`                       | `add_items_to_cart`, `bulk_add_to_cart`             | 1 or more, default 1                                                                                 |
| `modality`                       | `add_items_to_cart`, `bulk_add_to_cart`             | `PICKUP` or `DELIVERY`, uppercase. Default `PICKUP`.                                                 |
| `modality`                       | `remove_from_cart`                                  | `PICKUP` or `DELIVERY`. Without it, the item is removed in every modality.                           |
| `items`                          | `bulk_add_to_cart`                                  | At least one item. Each takes `product_id`, `quantity`, and `modality`, and no other keys.           |
| `limit`                          | `view_order_history`                                | 1 to 50, default 10                                                                                  |

## Error results

A tool that fails returns an MCP tool result with `isError` set to `true`. The model reads it like any other result, so it can correct its next call.

The text content says what went wrong, then `Next step:` and what to do, often naming the tool to call. A client that shows the model only text still passes on everything the model needs:

```text
Invalid arguments for add_items_to_cart:
  - quantity: Input should be greater than or equal to 1 (got -5)
  - modality: Input should be 'PICKUP' or 'DELIVERY' (got 'BOAT')
The tool did not run, so no request was sent.
Next step: Correct the arguments listed and call the tool again. The tool's input schema lists the valid values.
```

The structured content holds an `error` object with the same message and the details as fields. For a Kroger API error, the fields come from the `kroger-api` exception's [`to_dict()`](errors.md#the-to_dict-method):

```json
{
  "error": {
    "type": "not_found",
    "message": "Kroger API error 404 Not Found: (no error message in the response body)\n  request: GET /v1/chains/NOTACHAIN\n  correlation id: akam_1792607141_94d124d9-7609-4e01-a162-37dadf084c64\n  hint: No chain has this name. Get the valid names from the chains list.",
    "outcome_unknown": false,
    "status_code": 404,
    "status_text": "Not Found",
    "kroger_code": null,
    "kroger_message": null,
    "method": "GET",
    "url": "https://api.kroger.com/v1/chains/NOTACHAIN",
    "correlation_id": "akam_1792607141_94d124d9-7609-4e01-a162-37dadf084c64",
    "retry_after": null,
    "note": null,
    "hint": "No chain has this name. Get the valid names from the chains list.",
    "response_body": null,
    "next_step": "Get the valid chain names with list_chains.",
    "tool": "get_chain_details"
  }
}
```

Every `error` object has `type`, `message`, `next_step` (which can be `null`), and `tool`. The `type` is one of these:

| `type`                                          | Meaning                                                                                                                                                                                                                                        |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `invalid_arguments`                             | Arguments do not match the input schema. `errors` lists each one with `param`, `problem`, `error_code`, and `input` (left out for a missing argument).                                                                                         |
| `invalid_parameter`                             | A value passed the schema but not a `kroger-api` check, such as a search term of more than eight words. Has `param`, `value`, and `requirement`.                                                                                               |
| `location_required`                             | A product tool got no `location_id`, and no preferred location is set.                                                                                                                                                                         |
| `authentication_required`                       | The user is not signed in, or the sign-in has expired and cannot be renewed.                                                                                                                                                                   |
| `authentication_not_started`                    | `complete_authentication` was called with no sign-in in progress, for example after a server restart.                                                                                                                                          |
| `authorization_failed`                          | The redirect URL reports that the user refused access. Has `oauth_error` and `oauth_error_description`.                                                                                                                                        |
| `invalid_redirect_url`, `state_mismatch`        | The URL passed to `complete_authentication` has no code, or comes from another sign-in.                                                                                                                                                        |
| `bad_request`                                   | The Kroger API answered `400`.                                                                                                                                                                                                                 |
| `authentication_error`                          | The Kroger API answered `401`. From the token endpoint, the server's client ID or secret is wrong.                                                                                                                                             |
| `permission_denied`                             | The Kroger API answered `403`, usually because the token lacks the scope.                                                                                                                                                                      |
| `not_found`                                     | The Kroger API answered `404`, or a product search came back empty because its `location_id` does not exist.                                                                                                                                   |
| `rate_limited`                                  | The Kroger API answered `429`. The limits are daily, so the next step is to stop, not retry.                                                                                                                                                   |
| `server_error`, `api_error`, `invalid_response` | The Kroger API answered `5xx`, another error status, or a body that is not JSON.                                                                                                                                                               |
| `connection_error`, `timeout`                   | The Kroger API could not be reached, or did not answer within 30 seconds.                                                                                                                                                                      |
| `configuration_error`                           | A server setting, such as `KROGER_CLIENT_SECRET` or `KROGER_USER_ZIP_CODE`, is missing or invalid.                                                                                                                                             |
| `local_state_error`                             | The cart, order history, or preferences file cannot be read or written. Has `path`.                                                                                                                                                            |
| `empty_cart`                                    | `mark_order_placed` was called with nothing in the local cart tracking.                                                                                                                                                                        |
| `all_searches_failed`                           | Every search of a `bulk_search_products` call failed. `results` holds each search's error. If an error that stops the searches, such as a rate limit, leaves no search successful, the result has that error's `type` instead, with `results`. |
| `no_images`, `image_download_failed`            | The product has no image to return, or the download failed.                                                                                                                                                                                    |
| `unexpected_response`                           | A Kroger API response lacked the data the API documents.                                                                                                                                                                                       |
| `internal_error`                                | An unexpected exception in the server, probably a bug. Has `exception_type`.                                                                                                                                                                   |
| `tool_error`                                    | The MCP framework rejected the call for a reason other than its arguments.                                                                                                                                                                     |

Any other `type` is the `error_type` of a `kroger-api` exception, such as `not_authenticated`. See the [errors reference](errors.md#exception-hierarchy).

A cart add that fails with a timeout, a lost connection, or a `5xx` has `outcome_unknown: true`: Kroger may have added the items anyway. Its `next_step` says not to call the tool again until the user checks the cart in the Kroger app or website, because the Kroger API cannot read the cart. The local cart tracking is not updated. See [requests whose outcome is unknown](errors.md#requests-whose-outcome-is-unknown).

These cases are not errors:

- A search that finds nothing returns `count: 0` and a `message`.
- `get_preferred_location` with no preferred location returns `preferred_location_id: null`.
- A product search can return `api_warnings` from the Kroger API, such as `The following productIds were not found: 9999999999999`.
- A search of a `bulk_search_products` call can fail while the others succeed. That search has `success: false` and an `error`. An error that would fail every later search too, such as a rate limit or a network failure, stops the remaining searches: they have `searched: false`, and the result has `stopped_early` with the reason and next step. An invalid term or brand fails the whole call before any search runs.
- If the Kroger cart accepts items but the server cannot update its local cart tracking, for any reason, the result is a success with a `warning`, so the agent does not add the items a second time.
