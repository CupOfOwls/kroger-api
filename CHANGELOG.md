# Changelog

All notable changes to the `kroger-api` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
