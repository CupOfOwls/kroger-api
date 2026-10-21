---
sidebar_position: 2
title: Refresh tokens automatically
description: "Keep long-running kroger-api scripts authenticated without re-prompting the user, using stored refresh tokens."
---

# Refresh tokens automatically

Kroger access tokens expire after 30 minutes. If a script runs longer than this or runs on a schedule without user interaction, it must refresh the token without reopening a browser.

## Default behavior

Tokens obtained through `authenticate_user` are saved to a local token file with their refresh token, and with `expires_at`, the time they expire. The library loads the stored token on later runs and refreshes it if it has expired. The browser opens only if there is no stored token, or the token has expired and cannot be refreshed: Kroger rejects the refresh token, or the client cannot reach Kroger.

During a run, a request that gets `401` because the token has expired or been revoked is retried once: the client refreshes a user token, or requests a new client-credentials token, and resends the request. The client sends the refresh token from the token file first, because another process that shares the file may have saved a newer one, and then the one in memory if it differs. If that fails, the client raises `AuthenticationError`, and its `note` says why. See [401 recovery](../reference/errors.md#401-recovery).

## Refresh explicitly

For a long-running process, validate and refresh at your own checkpoints instead of relying on a failed call to trigger it.

```python
from kroger_api import KrogerAPI

kroger = KrogerAPI()
# Loads the stored token into the client and, if it has expired,
# refreshes it using the stored refresh token.
token_info = kroger.authorization.refresh_token_if_needed()
if token_info is None:
    print("No usable token. Sign the user in again.")
```

`refresh_token_if_needed` returns `None` when there is no stored token, when the token has expired and has no refresh token, or when Kroger rejects the refresh token. It raises other errors, such as `APIConnectionError` for a network failure, so you can tell them apart from a sign-in that must be repeated.

To check a token that is already on the client, call `test_current_token()`:

```python
if not kroger.test_current_token():
    print("The token has expired and cannot be refreshed. Sign the user in again.")
```

The check compares the token's expiry time with the clock and makes no API call, unless an expired token has to be refreshed. A token that Kroger revoked before it expired still passes this check; the next request then gets `401`, which the client handles as the previous section describes.

## Notes

- Client-credentials tokens do not have refresh tokens. Request a new one instead. This requires one call and no user interaction.
- Token files are created per flow, and per scope for client-credentials tokens; all user tokens share one file. If you clear them (`examples/clear_tokens.py`), the next run will require a full re-authentication.
- Token files live in `$KROGER_TOKEN_DIR` (default: your platform data directory, such as `~/.local/share/kroger-mcp/`), not the working directory. Do not commit or share them. They are credentials.
