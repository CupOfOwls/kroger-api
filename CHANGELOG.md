# Changelog

All notable changes to the `kroger-api` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - Unreleased

### Added

- **Exception hierarchy** (`kroger_api.errors`, also exported from the package root). Every error derives from `KrogerAPIError`; HTTP errors map to `BadRequestError` (400), `AuthenticationError` (401), `PermissionDeniedError` (403), `NotFoundError` (404), `RateLimitError` (429), and `InternalServerError` (5xx), all subclasses of `APIStatusError`. Each carries Kroger's error code and message (for example `PRODUCT-2017`, "Field 'term' must have three or more characters..."), the request method and URL, the `X-Correlation-Id` header, `Retry-After`, the parsed response body, and a hint for known causes. `to_dict()` returns the same details as JSON-safe data. Before this release, errors surfaced as `requests.HTTPError` with only "400 Client Error: Bad Request for url: ...", and the response body was discarded.
- **Parameter validation** (`kroger_api.validation`) against the constraints in the Kroger OpenAPI specs, confirmed against live responses. Invalid arguments raise `InvalidParameterError` (a `ValueError`) that names the parameter and the valid values, and no request is sent. This catches inputs the API accepts silently: an unknown or wrongly cased `fulfillment` type, a location search `limit` or `radius_in_miles` of 0, and a product search term with repeated spaces (which the API rejects with only "Invalid parameters"). The constraint constants are public for reuse in other schemas.
- `APIConnectionError` and `APITimeoutError` wrap network failures. Requests now time out after 30 seconds by default (previously they could wait forever); set `KrogerAPI(timeout=...)`.
- `ConfigurationError` for missing credentials or redirect URI, and `NotAuthenticatedError` for calls made before a token is obtained; both subclass `ValueError` as before. `InvalidResponseError` for a 2xx response whose body is not JSON.
- **`outcome_unknown`** on every exception: `True` when a request that changes data (a cart add) failed in a way that leaves its outcome unknown (a read timeout, a connection or TLS error that can come after sending, or a 5xx), so resending it could add the items twice. `APIConnectionError.request_sent` is `False` only when the request certainly did not reach Kroger: a DNS failure, a refused connection (to Kroger or to a proxy), a connect timeout, or a rejected certificate. Other TLS and proxy errors can come after the request was sent. Messages and hints for these errors say to check the cart before resending.
- Every exception can be pickled, so it can cross a process boundary.
- `kroger_api.utils.env.load_env_file()` and `kroger_api.token_storage.USER_TOKEN_FILE`.
- `get_token_with_authorization_code(..., token_file=...)` saves the new user token to that file instead of `.kroger_token_user.json`.
- `AuthorizationAPI.load_saved_token(token_file=None)` loads a saved user token and renews it if it has expired, like `refresh_token_if_needed`, but says why it cannot: it raises `NotAuthenticatedError` when there is no saved token or no refresh token, and `BadRequestError`, with Kroger's message, when Kroger rejects the refresh token. `refresh_token_if_needed` returns `None` in those cases, as before.
- `kroger_api.token_storage.token_file_lock(token_file)` and `kroger_api.utils.locking.file_lock(path)`: an exclusive lock on a file (`<file>.lock`, through `flock`, or `msvcrt.locking` on Windows) that the threads of a process and other processes respect. It is reentrant within a thread, ends with the process that holds it, and after 90 seconds, or on a file system without locks, lets the caller go on without it and logs a warning.

### Fixed

- **Automatic token refresh on 401 never ran.** The client looked for `{"error": "invalid_token"}` in the body, but the Kroger API gateway returns `{"message": "Unauthorized"}` and signals `invalid_token` only in the `WWW-Authenticate` header. Any 401 now triggers one recovery, and the request is retried once. A user token is refreshed with the refresh token from the token file first, which another process may have rotated, and then with the one in memory if it differs, so a refresh token that was already used is not sent while a newer one exists. A client-credentials token obtained with `get_token_with_client_credentials` is re-requested; no other token is ever replaced with a client-credentials token. A token request that fails for a reason other than a rejected refresh token, such as a network failure or rejected client credentials, is raised as itself rather than as the original 401.
- **`test_token` treated every token as invalid.** It probed `/v1/connect/oauth2/profile`, which does not exist (it returns 404 for any token), so every check failed: client-credentials tokens were re-requested and user tokens refreshed on every check, costing up to four extra requests per kroger-mcp tool call. Tokens now record `expires_at` when issued, and the check compares it with the clock. Token files saved by earlier versions get their expiry from the file's modification time.
- Product search `limit=0` and `start=0` were dropped silently because of a truthiness check. `limit=0` now raises `InvalidParameterError`, and `start=0` is sent.
- Path parameters are URL-quoted, so chain names with spaces or apostrophes (`"LOAF 'N JUG"`) work.
- A refresh response without a new refresh token no longer discards the existing one (RFC 6749 section 6).
- `get_authorization_url` without a redirect URI raises `ConfigurationError`. It used to build a URL with `redirect_uri=None` in it.
- `refresh_token_if_needed` puts an unexpired saved token on the client, so the next call uses it, and saves a refreshed token back to the file it came from. It returns `None` when the refresh token is rejected, and raises other errors, such as a network failure, instead of returning `None` for them too. It changes the client's token file only when it uses or refreshes the saved token, so a later save cannot put a client-credentials token in a user token file.
- `authenticate_user(token_file=...)` saves a new sign-in to that file and leaves `.kroger_token_user.json` unchanged. It always saved to `.kroger_token_user.json`.
- **Two processes or threads that renew the same saved token at once no longer sign each other out.** Kroger issues a new refresh token with each refresh, so the second of two simultaneous refreshes sent a refresh token that was already used, and Kroger rejected it (or, with reuse detection, revoked the sign-in). Renewing a saved user token now holds a lock on its token file: `refresh_token_if_needed`, `load_saved_token`, `test_current_token`, and the 401 retry. A process or thread that waited for the lock uses the token that the other one saved, if it was issued later, and sends no refresh request. If every refresh token is rejected, the file is read once more, in case a process that does not take the lock (an earlier version) renewed the token meanwhile. A thread whose request got a 401 after another thread replaced the client's token resends the request with that token.
- A new sign-in (`get_token_with_authorization_code`) and `clear_token` wait for a refresh that is in progress, so the refresh cannot overwrite the new sign-in or save the deleted token again.
- `get_authorization_url` percent-encodes every parameter. A redirect URI with a query string (`&`), or a `state` or `banner` with reserved characters, broke the authorization URL, and the spaces between scopes were not encoded.
- `extract_port_from_redirect_uri` returns 80 or 443 for a redirect URI without a port, such as `http://localhost/callback`. It raised `ValueError`.

### Security

- **`authenticate_user` uses PKCE** (RFC 7636). The code exchange needs a verifier that never leaves the process, so an authorization code that another program intercepts from the redirect to `localhost` cannot be used. It did not use PKCE, although the library supports it and kroger-mcp's sign-in used it.
- `generate_random_state` uses the `secrets` module. It used `random`, whose output can be predicted, for the OAuth state that guards against cross-site request forgery.
- `save_token` writes a temporary file that is private (mode 600) from the moment it is created, then replaces the token file with it. It used to write the token file with default permissions and restrict them afterward, and a failed or concurrent write could leave a half-written file.

### Changed

- `location_exists`, `chain_exists`, and `department_exists` raise `InvalidParameterError` for a malformed ID instead of a 400 `HTTPError`; they still return `False` for a well-formed ID that does not exist.
- An empty string passed for an optional filter (`brand=""`, `location_id=""`) now raises `InvalidParameterError` instead of being dropped. Pass `None` to omit a filter.
- Arguments that fail a parameter check raise `InvalidParameterError`, a `ValueError`, before any request. Earlier versions sent them, and the API's 400 arrived as a `requests.HTTPError`, so `except requests.exceptions.HTTPError` no longer catches these cases. Catch `KrogerAPIError` to handle both.
- A product search needs a `term` or a `product_id`. A search by `brand` alone, which the Products spec lists as valid, raises `InvalidParameterError`: the live API rejects it with 400 `PRODUCT-2016`.
- Library messages (token loading, refreshing, and the like) go through the standard `logging` module under the `kroger_api` loggers, instead of `print` to stderr. Warnings still appear by default; informational messages appear only when logging is configured for them. Loading a token file no longer prints a line every time. The interactive `authenticate_user` flow still prints its prompts.
- The `KROGER_*` settings in a `.env` file in the working directory are read when a client is created, as the documentation says. Other variables in the file, such as a proxy or CA bundle setting, and `.env` files in parent directories are ignored. `load_and_validate_env` also reads the names it is asked to check. The file was read when the package was imported, starting from the package's own directory and searching upward, and every variable in it was loaded. Run scripts from the directory that holds `.env`.
- `validation.cart_items` accepts a tuple of items and returns a list.
- `lat_long`, `lat`, and `lon` are sent without surrounding whitespace, and numbers are written without an exponent. A string must be a plain decimal number: an exponent, `nan`, or `inf` raises `InvalidParameterError`.
- `add_to_cart` does not parse the response body, so a `2xx` answer is a success even when the body is not valid JSON.

## [0.3.1] - 2026-07-08

### Fixed

- Library diagnostics (token status messages, refresh warnings) are printed to stderr instead of stdout. Stray stdout output corrupts the JSON-RPC framing of stdio-based MCP servers built on this library, such as kroger-mcp. Interactive OAuth console prompts still use stdout.

## [0.3.0] - 2026-07-08

### Changed

- **Token storage moved out of the working directory** (fixes #6): token files are now written to a per-user data directory instead of the CWD, so the library works when the process is launched with a read-only working directory (e.g. MCP servers under Claude Desktop on Windows). Resolution order:
  1. `$KROGER_TOKEN_DIR` environment variable, if set (thanks @AMaini503, #5)
  2. `$XDG_DATA_HOME/kroger-mcp/` (default `~/.local/share/kroger-mcp/`) on Unix-like systems
  3. `%APPDATA%\kroger-mcp\` on Windows
- Absolute token file paths are passed through unchanged
- Token files are written with `0600` permissions (fixes CupOfOwls/kroger-mcp#13)

### Added

- Initial unit test suite for token retrieval and authorization URL construction (thanks @AveTravolta, #4)
- `KrogerClient` re-exported from the package root

## [0.2.0] - 2025-05-28

### Added

- **PKCE Support**: Added Proof Key for Code Exchange (PKCE) support for enhanced security in the OAuth flow
  - New `code_challenge` and `code_challenge_method` parameters in `get_authorization_url()`
  - New `code_verifier` parameter in `get_token_with_authorization_code()`
  - New utility module `pkce.py` with helper functions:
    - `generate_code_verifier()`: Generate a random code verifier
    - `generate_code_challenge()`: Generate a code challenge from a code verifier
    - `generate_pkce_parameters()`: Generate all PKCE parameters in one call

### Security

- Enhanced OAuth security with PKCE support, mitigating authorization code interception attacks
- Improved token exchange with better error handling for PKCE flows

## [0.1.0] - 2025-05-23

### Added

- Initial release of the Kroger API client library
- Support for OAuth 2.0 authorization code flow and client credentials flow
- API access for products, locations, cart, identity, and more
- Token storage and automatic refresh
- Flexible token management with custom file paths
- Example scripts for common use cases
