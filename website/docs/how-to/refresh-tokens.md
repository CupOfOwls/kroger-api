---
sidebar_position: 2
title: Refresh tokens automatically
description: "Keep long-running kroger-api scripts authenticated without re-prompting the user, using stored refresh tokens."
---

# Refresh tokens automatically

Kroger access tokens expire after 30 minutes. If a script runs longer than this or runs on a schedule without user interaction, it must refresh the token without reopening a browser.

## Default behavior

Tokens obtained through `authenticate_user` are saved to a local token file with their refresh token, and with `expires_at`, the time they expire. The library loads the stored token on later runs and refreshes it if it has expired. The browser opens only if there is no stored token, or the token has expired and cannot be refreshed: Kroger rejects the refresh token, or the client cannot reach Kroger.

During a run, a request that gets `401` because the token has expired or been revoked is retried once: the client renews a user token, or requests a new client-credentials token, and resends the request. If that fails, the client raises `AuthenticationError`, and its `note` says why. See [401 recovery](../reference/errors.md#401-recovery).

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

To know why there is no usable token, call `load_saved_token` instead. It does the same work, and raises `NotAuthenticatedError` when there is no stored token or no refresh token, and `BadRequestError`, with Kroger's message, when Kroger rejects the refresh token:

```python
from kroger_api.errors import BadRequestError, NotAuthenticatedError

try:
    kroger.authorization.load_saved_token()
except NotAuthenticatedError as e:
    print(f"Sign the user in: {e.message}")
except BadRequestError as e:
    print(f"Kroger rejected the refresh token: {e.kroger_message}")
```

To check a token that is already on the client, call `test_current_token()`:

```python
if not kroger.test_current_token():
    print("The token has expired and cannot be refreshed. Sign the user in again.")
```

The check compares the token's expiry time with the clock and makes no API call, unless an expired token has to be refreshed. A token that Kroger revoked before it expired still passes this check; the next request then gets `401`, which the client handles as the previous section describes.

## Share a sign-in between processes

Several processes can use the same token file, for example a script and a `kroger-mcp` server, or two `kroger-mcp` servers. Kroger issues a new refresh token with each refresh, and a refresh token that was already used can be rejected. If two processes refreshed the same expired token at the same moment, one of them would be signed out.

So the client renews a saved token while it holds a lock on the token file:

1. It waits for the lock, which is a separate file named after the token file with `.lock` added. A thread of the same process waits in the same way.
1. It reads the token file again. If another process renewed the token while this one waited, the client uses the saved token and sends no refresh request.
1. Otherwise it refreshes the token, saves it, and releases the lock.

`refresh_token_if_needed`, `load_saved_token`, `test_current_token`, and the `401` retry all work this way. A new sign-in and `clear_token` also wait for the lock, so a refresh that is in progress cannot overwrite them. After `clear_token` deletes the file, a process that still holds the old token in memory cannot renew it: the user has signed out and must sign in again.

The lock ends when the process that holds it does, so a crashed process never leaves the file locked. If the lock is not free after 90 seconds, or the file system does not support locks, the client logs a warning and goes on without it. Use `kroger_api.token_storage.token_file_lock` to hold the lock in your own code, for example while you replace a token file by hand.

## Notes

- Client-credentials tokens do not have refresh tokens. Request a new one instead. This requires one call and no user interaction.
- Token files are created per flow, and per scope for client-credentials tokens; all user tokens share one file. If you clear them (`examples/clear_tokens.py`), the next run will require a full re-authentication.
- Token files live in `$KROGER_TOKEN_DIR` (default: your platform data directory, such as `~/.local/share/kroger-mcp/`), not the working directory. Do not commit or share them. They are credentials.
