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

### Fixed

- **Automatic token refresh on 401 never ran.** The client looked for `{"error": "invalid_token"}` in the body, but the Kroger API gateway returns `{"message": "Unauthorized"}` and signals `invalid_token` only in the `WWW-Authenticate` header. Any 401 now triggers one recovery: a user token is refreshed, a client-credentials token is re-requested, and the request is retried once.
- **`test_token` treated every token as invalid.** It probed `/v1/connect/oauth2/profile`, which does not exist (it returns 404 for any token), so every check failed: client-credentials tokens were re-requested and user tokens refreshed on every check, costing up to four extra requests per kroger-mcp tool call. Tokens now record `expires_at` when issued, and the check compares it with the clock. Token files saved by earlier versions get their expiry from the file's modification time.
- Product search `limit=0` and `start=0` were dropped silently because of a truthiness check. `limit=0` now raises `InvalidParameterError`, and `start=0` is sent.
- Path parameters are URL-quoted, so chain names with spaces or apostrophes (`"LOAF 'N JUG"`) work.
- A refresh response without a new refresh token no longer discards the existing one (RFC 6749 section 6).
- `get_authorization_url` without a redirect URI raises `ConfigurationError`. It used to build a URL with `redirect_uri=None` in it.
- `refresh_token_if_needed` puts an unexpired saved token on the client, so the next call uses it, and saves a refreshed token back to the file it came from. It returns `None` when the refresh token is rejected, and raises other errors, such as a network failure, instead of returning `None` for them too.

### Changed

- `location_exists`, `chain_exists`, and `department_exists` raise `InvalidParameterError` for a malformed ID instead of a 400 `HTTPError`; they still return `False` for a well-formed ID that does not exist.
- An empty string passed for an optional filter (`brand=""`, `location_id=""`) now raises `InvalidParameterError` instead of being dropped. Pass `None` to omit a filter.

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
