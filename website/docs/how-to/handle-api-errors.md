---
sidebar_position: 3
title: Handle API errors
description: "Catch kroger-api exceptions by type, show what went wrong, retry only the failures a retry can fix, and log the details Kroger support asks for."
---

# Handle API errors

This guide shows you how to catch the exceptions that `kroger-api` raises and decide what to do about each one. For the full list of classes and attributes, see the [errors reference](../reference/errors.md).

## Catch errors by type

Catch the most specific class you can act on, then `KrogerAPIError` for everything else. Every exception the library raises about a request derives from it.

```python
from kroger_api import KrogerAPI, KrogerAPIError, InvalidParameterError, NotFoundError

kroger = KrogerAPI()
kroger.authorization.get_token_with_client_credentials("product.compact")

location_id = "99999999"
try:
    store = kroger.location.get_location(location_id)
except InvalidParameterError as e:
    print(f"That store ID {e.requirement}.")
except NotFoundError:
    print(f"No store has the ID {location_id}.")
except KrogerAPIError as e:
    print(e)
```

`InvalidParameterError` means the client found a problem with an argument and sent no request. Its `requirement` says what a valid value looks like, for example `must be an 8-character store locationId such as '01400513'`.

## Show what went wrong

The message of each exception is complete enough to show to a developer as-is. For an API error, it holds the HTTP status, Kroger's explanation and error code, the request, the correlation ID, and a hint when the cause is known:

```text
Kroger API error 404 Not Found: (no error message in the response body)
  request: GET /v1/locations/99999999
  correlation id: akam_1792607141_ec02f117-d8d0-46c9-8dbe-ba9a40b637ab
  hint: No store has this locationId. Find valid IDs with a location search.
```

To build your own message, read the attributes instead: `status_code`, `kroger_code`, `kroger_message`, `hint`, and the others in the [API error attributes](../reference/errors.md#api-error-attributes) table.

## Retry only what a retry can fix

A retry helps only when the failure is temporary. Retry a network failure or a `5xx` response once, after a short wait. Do not retry other errors: the same request fails the same way.

```python
import time

from kroger_api import APIConnectionError, InternalServerError


def call_with_one_retry(call, delay_seconds=5):
    try:
        return call()
    except (APIConnectionError, InternalServerError):
        time.sleep(delay_seconds)
        return call()


products = call_with_one_retry(
    lambda: kroger.product.search_products(term="milk", location_id="01400513")
)
```

`APIConnectionError` also covers `APITimeoutError`. The client already handles one case of `401` itself: it gets a new token and resends the request once, as the [401 recovery](../reference/errors.md#401-recovery) section describes.

| Error                                         | What to do                                                                                                    |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `InvalidParameterError`, `BadRequestError`    | Correct the argument that `param` or `kroger_message` names.                                                  |
| `AuthenticationError` from a cart call        | Sign the user in again with the authorization-code flow.                                                      |
| `AuthenticationError` from the token endpoint | Correct `KROGER_CLIENT_ID` and `KROGER_CLIENT_SECRET`.                                                        |
| `PermissionDeniedError`                       | Use a token with the scope the endpoint needs. Cart calls need a user token.                                  |
| `NotFoundError`                               | Look up a valid ID with a search or list call.                                                                |
| `RateLimitError`                              | Stop and resume after the daily limit resets. See [Handle rate limits and pagination](handle-rate-limits.md). |
| `InternalServerError`, `APIConnectionError`   | Retry once after a short wait.                                                                                |
| `ConfigurationError`                          | Set the missing environment variable or argument.                                                             |

## Log the details

Log `to_dict()` to keep every detail in a form that log tools can search. Include the correlation ID when you report a problem to Kroger: it identifies the request in their logs.

```python
import json
import logging

try:
    kroger.cart.add_to_cart([{"upc": "0001111041700", "quantity": 1, "modality": "PICKUP"}])
except KrogerAPIError as e:
    logging.error("Kroger API call failed: %s", json.dumps(e.to_dict()))
    raise
```

## Check user input early

The same checks the client runs before a request are available in `kroger_api.validation`. Use them to reject bad input, such as a ZIP code typed into a form, before your code reaches the API call.

```python
from kroger_api import InvalidParameterError, validation

try:
    zip_code = validation.zip_code(user_input)
except InvalidParameterError as e:
    print(f"The ZIP code {e.requirement}.")
```

For `"45202-1234"`, this prints `The ZIP code must be a 5-digit ZIP code (ZIP+4 is not accepted).` The [parameter checks](../reference/errors.md#parameter-checks) table lists the other checks and their constants.

## Treat empty results as possible mistakes

Some mistakes return an empty result instead of an error, so check for them when a result is empty:

- A product search with a `location_id` that does not exist returns no products. Confirm the store with `kroger.location.location_exists(location_id)`.
- A product search by `product_id` returns `meta.warnings`, such as `The following productIds were not found: 9999999999999`, for IDs it does not know.

## Keep older error handling working

Code written for earlier versions keeps working, because the HTTP and network errors also derive from the `requests` exceptions:

```python
import requests

try:
    kroger.location.get_location("99999999")
except requests.exceptions.HTTPError as e:
    print(e.response.status_code)  # 404
```

Change `except requests.exceptions.HTTPError` to `except APIStatusError` when you want the parsed details, such as `kroger_message`.
