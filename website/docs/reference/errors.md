---
sidebar_position: 2
title: kroger-api errors reference
description: "The exceptions kroger-api raises, the details each one carries, how HTTP statuses map to them, and the parameter checks that run before a request is sent."
---

# kroger-api errors reference

This page lists the exceptions that `kroger-api` raises and the details each one carries. All of them are in the `kroger_api.errors` module, and the package root exports the same classes, so `from kroger_api import NotFoundError` also works. For examples of catching them, see [Handle API errors](../how-to/handle-api-errors.md).

## Exception hierarchy

Every exception derives from `KrogerAPIError`, so one `except KrogerAPIError` catches any error the library raises about a request.

```text
KrogerAPIError
├── ConfigurationError        (also ValueError)
├── InvalidParameterError     (also ValueError)
├── NotAuthenticatedError     (also ValueError)
├── APIConnectionError        (also requests.exceptions.ConnectionError)
│   └── APITimeoutError       (also requests.exceptions.Timeout)
├── APIStatusError            (also requests.exceptions.HTTPError)
│   ├── BadRequestError       400
│   ├── AuthenticationError   401
│   ├── PermissionDeniedError 403
│   ├── NotFoundError         404
│   ├── RateLimitError        429
│   └── InternalServerError   5xx
└── InvalidResponseError
```

| Class                   | `error_type`           | Raised when                                                                                            |
| ----------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------ |
| `ConfigurationError`    | `configuration_error`  | The client ID, client secret, or redirect URI is missing.                                              |
| `InvalidParameterError` | `invalid_parameter`    | An argument fails a [parameter check](#parameter-checks). No request is sent.                          |
| `NotAuthenticatedError` | `not_authenticated`    | A method that calls the API runs before the client has an access token.                                |
| `APIConnectionError`    | `connection_error`     | The request gets no HTTP response: DNS failure, refused or reset connection, or TLS error.             |
| `APITimeoutError`       | `timeout`              | No response arrives within the client's timeout.                                                       |
| `APIStatusError`        | `api_error`            | The Kroger API answers with a status that has no subclass below, such as `405`.                        |
| `BadRequestError`       | `bad_request`          | The Kroger API answers `400`.                                                                          |
| `AuthenticationError`   | `authentication_error` | The Kroger API answers `401`, after one attempt to get a new token. See [401 recovery](#401-recovery). |
| `PermissionDeniedError` | `permission_denied`    | The Kroger API answers `403`.                                                                          |
| `NotFoundError`         | `not_found`            | The Kroger API answers `404`.                                                                          |
| `RateLimitError`        | `rate_limited`         | The Kroger API answers `429`.                                                                          |
| `InternalServerError`   | `server_error`         | The Kroger API answers with a `5xx` status.                                                            |
| `InvalidResponseError`  | `invalid_response`     | A `2xx` response has a body that is not valid JSON.                                                    |

Because the HTTP and network errors also derive from the matching `requests` exceptions, code written for earlier versions, such as `except requests.exceptions.HTTPError as e: e.response.status_code`, still catches every error response from the Kroger API. An argument that fails a [parameter check](#parameter-checks) is different. Earlier versions sent it, and the API's `400` arrived as an `HTTPError`. Now the client sends no request and raises `InvalidParameterError`, which is a `ValueError`, not an `HTTPError`. Catch `KrogerAPIError` to handle both.

## API error attributes

`APIStatusError` and its subclasses carry these attributes. A value is `None` when the response does not include it.

| Attribute        | Type                | Description                                                                                                                      |
| ---------------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `status_code`    | `int`               | The HTTP status, for example `404`.                                                                                              |
| `status_text`    | `str`               | The HTTP reason phrase, for example `Not Found`.                                                                                 |
| `kroger_code`    | `str` or `None`     | Kroger's error code, for example `PRODUCT-2017` or `AUTH-1007`. From the token endpoint, an OAuth error such as `invalid_scope`. |
| `kroger_message` | `str` or `None`     | Kroger's explanation, for example `Field 'term' allows for a maximum of 8 individual terms per search`.                          |
| `method`         | `str`               | The HTTP method of the request.                                                                                                  |
| `url`            | `str`               | The full request URL, with the query string. It holds no credentials: the access token travels in a header.                      |
| `body`           | any                 | The parsed JSON body, the raw text if it is not JSON, or `None` if it is empty.                                                  |
| `correlation_id` | `str` or `None`     | The `X-Correlation-Id` response header. Quote it when you report a problem to Kroger.                                            |
| `retry_after`    | `float` or `None`   | Seconds to wait, from a `Retry-After` header.                                                                                    |
| `note`           | `str` or `None`     | What the client did before raising, for example that it retried with a new token.                                                |
| `hint`           | `str` or `None`     | The usual cause and fix, for the cases in [hints](#hints).                                                                       |
| `response`       | `requests.Response` | The response itself, inherited from `requests.exceptions.HTTPError`.                                                             |

The other exceptions carry these attributes:

| Class                   | Attributes                                                                                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `InvalidParameterError` | `param` (the argument's name, such as `limit` or `items[2].upc`), `value`, `requirement`                                                                              |
| `APIConnectionError`    | `method`, `url`, `reason` (the text of the underlying `requests` exception, also on `__cause__`), `request_sent` (`False` if the client never connected, else `None`) |
| `APITimeoutError`       | The `APIConnectionError` attributes and `timeout` (seconds)                                                                                                           |
| `InvalidResponseError`  | `status_code`, `method`, `url`, `correlation_id`, `body` (the first 2,000 characters)                                                                                 |

Every exception has `message`, which is also its `str()`, `error_type`, a short, stable category for programs to branch on, and `outcome_unknown`, described in the next section. Every exception can be pickled, so it can cross a process boundary, for example from a `ProcessPoolExecutor` worker.

## Requests whose outcome is unknown

The `outcome_unknown` attribute is `True` when a failed request may have changed data anyway, so sending it again could repeat the change. In `kroger-api`, a cart add is the only request that changes data, and a repeated add puts the items in the cart twice. For such a request, these errors set the attribute:

| Error                  | Why the outcome is unknown                                                                                                                                                                                              |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `APITimeoutError`      | Kroger may have processed the request without answering in time. A timeout while connecting does not count: the request was never sent.                                                                                 |
| `APIConnectionError`   | The connection failed after the request may have been sent. When the client never connected (a DNS failure, a refused connection, or a TLS or proxy error), `request_sent` is `False` and `outcome_unknown` is `False`. |
| `InternalServerError`  | A gateway can answer `5xx` after the request was processed.                                                                                                                                                             |
| `InvalidResponseError` | The `2xx` status says the request was processed. Only the body cannot be read.                                                                                                                                          |

Reads (`GET` and `HEAD`) and token requests always have `outcome_unknown` set to `False`, because sending them again changes nothing. When it is `True`, the message ends with advice to check the effect before you send the request again. The Kroger API has no endpoint that reads the cart, so the user checks it in the Kroger app or website.

## Error message

The message of an API error states the status, Kroger's explanation and code, the request, and the correlation ID, then any note and hint. This is the message for a cart call made with a client-credentials token:

```text
Kroger API error 403 Forbidden: Invalid token on request [AUTH-1007]
  request: PUT /v1/cart/add
  correlation id: akam_1792605135_03872bcb-a087-48af-982e-ba540dde3e38
  hint: This endpoint needs a user access token from the authorization-code flow, with the cart.basic:write scope for the cart or profile.compact for the profile. A client-credentials token is always refused here.
```

When the response body has no explanation, as with most `404` responses, the first line says so:

```text
Kroger API error 404 Not Found: (no error message in the response body)
  request: GET /v1/locations/99999999
  correlation id: akam_1792607141_ec02f117-d8d0-46c9-8dbe-ba9a40b637ab
  hint: No store has this locationId. Find valid IDs with a location search.
```

## Error body shapes

The Kroger API returns errors in several shapes, depending on which layer rejects the request. `kroger-api` reads `kroger_code` and `kroger_message` from each of them.

| Shape                                         | Where it comes from                                                                                                       |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `{"errors": {"code", "reason", "timestamp"}}` | Products and Locations APIs                                                                                               |
| `{"code", "reason", "timestamp"}`             | `403` from the Cart and Identity APIs                                                                                     |
| `{"error", "error_description"}`              | The OAuth token endpoint                                                                                                  |
| `{"message": "Unauthorized"}`                 | The API gateway's `401`. The `WWW-Authenticate` header then carries `error="invalid_token"`, which becomes `kroger_code`. |
| Empty                                         | Most `404` responses, and every response to a `HEAD` request                                                              |

## Hints

The `hint` attribute explains known causes. The client sets it in these cases:

| Response                                              | Hint says                                                                                                         |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `401` from the token endpoint                         | The client ID or secret is wrong.                                                                                 |
| `400 invalid_scope` from the token endpoint           | Request only the scopes enabled for the app.                                                                      |
| `400` from the token endpoint about the refresh token | The refresh token is invalid or expired, so the user must sign in again.                                          |
| `400` from the token endpoint about the code          | The authorization code is invalid, expired, or already used, or the redirect URI or PKCE verifier does not match. |
| `400 Invalid parameters` from the Products API        | The usual causes: a search term of more than eight words, or a malformed product ID list.                         |
| `401`                                                 | The access token is missing, invalid, or expired.                                                                 |
| `403` from the Cart or Identity API                   | The endpoint needs a user token with the right scope.                                                             |
| `403` from other endpoints                            | The token lacks the scope the endpoint requires.                                                                  |
| `404`                                                 | Which ID or name does not exist (store, product, chain, or department), and where to find valid ones.             |
| `429`                                                 | The daily rate limit is used up, so an immediate retry fails too.                                                 |
| `5xx`                                                 | The Kroger API failed; a later retry may succeed. For a cart add, the request may have been processed anyway.     |

## The to_dict() method

Every exception has a `to_dict()` method that returns its details as data you can serialize to JSON, for logs or for another program. `kroger-mcp` uses it to build its [error results](mcp-tools.md#error-results). This is the dictionary for the `404` above:

```json
{
  "type": "not_found",
  "message": "Kroger API error 404 Not Found: (no error message in the response body)\n  request: GET /v1/locations/99999999\n  correlation id: akam_1792607141_ec02f117-d8d0-46c9-8dbe-ba9a40b637ab\n  hint: No store has this locationId. Find valid IDs with a location search.",
  "outcome_unknown": false,
  "status_code": 404,
  "status_text": "Not Found",
  "kroger_code": null,
  "kroger_message": null,
  "method": "GET",
  "url": "https://api.kroger.com/v1/locations/99999999",
  "correlation_id": "akam_1792607141_ec02f117-d8d0-46c9-8dbe-ba9a40b637ab",
  "retry_after": null,
  "note": null,
  "hint": "No store has this locationId. Find valid IDs with a location search.",
  "response_body": null
}
```

An `InvalidParameterError` adds `param`, `value`, and `requirement`. A connection error adds `method`, `url`, `reason`, and `request_sent`, and a timeout also adds `timeout`.

## Parameter checks

The client checks arguments against the constraints in the Kroger OpenAPI specifications before it sends a request, and raises `InvalidParameterError` if one fails. Some of these values the Kroger API would reject with a `400`; others it accepts and ignores, which returns results that look valid but are not filtered. The constants are public in `kroger_api.validation`, so other code can reuse them.

| Parameter                     | Valid values                                                                                                                                            | Constant                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Product search `term`         | At least three characters, not counting leading and trailing spaces. At most eight words, split on single spaces, so each extra space counts as a word. | `PRODUCT_TERM_MIN_LENGTH`, `PRODUCT_TERM_MAX_WORDS` |
| Product search `limit`        | 1 to 50                                                                                                                                                 | `PRODUCT_LIMIT_MIN`, `PRODUCT_LIMIT_MAX`            |
| Product search `start`        | 0 to 250                                                                                                                                                | `PRODUCT_START_MIN`, `PRODUCT_START_MAX`            |
| `fulfillment`                 | A comma-separated list of `ais`, `csp`, `dth`, and `sth`, lowercase. The API ignores any other value.                                                   | `FULFILLMENT_TYPES`                                 |
| `location_id`                 | Eight letters or digits                                                                                                                                 | `LOCATION_ID_PATTERN`                               |
| `product_id`, cart `upc`      | 13 digits                                                                                                                                               | `PRODUCT_ID_PATTERN`                                |
| `department`, `department_id` | Two letters or digits                                                                                                                                   | `DEPARTMENT_ID_PATTERN`                             |
| `zip_code`                    | Five digits. ZIP+4 is not accepted.                                                                                                                     | `ZIP_CODE_PATTERN`                                  |
| `radius_in_miles`             | 1 to 100. The API ignores 0.                                                                                                                            | `LOCATION_RADIUS_MIN`, `LOCATION_RADIUS_MAX`        |
| Location search `limit`       | 1 to 200. The API ignores 0.                                                                                                                            | `LOCATION_LIMIT_MIN`, `LOCATION_LIMIT_MAX`          |
| `lat`, `lon`, `lat_long`      | Decimal degrees: latitude from -90 to 90, longitude from -180 to 180. `lat_long` is `"latitude,longitude"`.                                             | None                                                |
| Cart item `quantity`          | An integer of 1 or more                                                                                                                                 | None                                                |
| Cart item `modality`          | `PICKUP` or `DELIVERY`, uppercase                                                                                                                       | `CART_MODALITIES`                                   |

Optional filters must be `None` to be left out. An empty string, such as `brand=""`, raises `InvalidParameterError`. Integer parameters also accept strings of digits, such as `"10"`.

## 401 recovery

When a request gets a `401`, the client tries once to get a new token and resend the request:

1. A user token is refreshed with its refresh token. If Kroger rejects that refresh token and the token file holds a different one, the client tries the one from the file too: another process that shares the file may have refreshed the token since this client loaded it.
1. A client-credentials token from `get_token_with_client_credentials` is replaced with a new one for the same scope.

Any other token is not replaced. A user token without a refresh token, for example, is never swapped for a client-credentials token, even after you switch the client to client credentials and back.

If there is no way to get a new token, Kroger rejects the refresh token, or the resent request also gets a `401`, the client raises `AuthenticationError`, and its `note` says which of these happened. If the token request fails for another reason, the client raises that error instead, because its message describes the real problem: an `APIConnectionError` for the token endpoint when the network is down, or an `AuthenticationError` from the token endpoint, whose hint says the client ID or secret is wrong.

## Timeouts

Each request waits at most 30 seconds (`kroger_api.client.DEFAULT_TIMEOUT`) for a response, then raises `APITimeoutError`. Set a different limit with `KrogerAPI(timeout=60)`, or `timeout=None` to wait indefinitely.
