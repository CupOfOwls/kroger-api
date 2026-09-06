---
sidebar_position: 2
title: Refresh tokens automatically
description: "Keep long-running kroger-api scripts authenticated without re-prompting the user, using stored refresh tokens."
---

# Refresh tokens automatically

Kroger access tokens expire after 30 minutes. If a script runs longer than this or runs on a schedule without user interaction, it must refresh the token without reopening a browser.

## Default behavior

Tokens obtained through `authenticate_user` are saved to a local token file with their refresh token. The library loads the stored token on later runs and refreshes it if necessary. The browser only opens if there is no refresh token available.

## Refresh explicitly

For a long-running process, validate and refresh at your own checkpoints instead of relying on a failed call to trigger it.

```python
from kroger_api import KrogerAPI

kroger = KrogerAPI()
# Tests the stored access token and, if it no longer validates,
# refreshes it using the stored refresh token.
kroger.authorization.refresh_token_if_needed()
```

Or test-then-refresh, like `examples/token_refresh_example.py`:

```python
from kroger_api.token_storage import load_token

token_info = load_token(".kroger_token_user.json")
if token_info:
    kroger.client.token_info = token_info
    if not kroger.test_current_token():
        kroger.authorization.refresh_token(token_info["refresh_token"])
```

## Notes

- Client-credentials tokens do not have refresh tokens. Request a new one instead. This requires one call and no user interaction.
- Token files are created per flow, and per scope for client-credentials tokens; all user tokens share one file. If you clear them (`examples/clear_tokens.py`), the next run will require a full re-authentication.
- Token files live in `$KROGER_TOKEN_DIR` (default: your platform data directory, such as `~/.local/share/kroger-mcp/`), not the working directory. Do not commit or share them. They are credentials.
