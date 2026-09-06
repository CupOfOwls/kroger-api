---
sidebar_position: 1
title: Choose an auth flow
description: "Decide between client credentials, authorization code, and PKCE for a given Kroger API task, with the kroger-api calls for each."
---

# Choose an auth flow

The Kroger API supports three OAuth2 flows. Choose the one based on whose data you are accessing and where your code is running.

## Decision table

| Your task                                                                                  | Flow                      |
| ------------------------------------------------------------------------------------------ | ------------------------- |
| Read public data: stores, products, chains, departments                                    | Client credentials        |
| Act on a user's account: cart, profile                                                     | Authorization code        |
| Act on a user's account from an environment where the client secret cannot be kept private | Authorization code + PKCE |

## Client credentials

The app authenticates as itself. There is no user sign-in, browser, or consent screen, so it cannot access data tied to a user account. Use it for catalog and location lookups:

```python
from kroger_api import KrogerAPI

kroger = KrogerAPI()
kroger.authorization.get_token_with_client_credentials("product.compact")
```

## Authorization code

The user signs in and grants scopes. `kroger-api` manages the process by opening the browser, running a local callback server on your `KROGER_REDIRECT_URI`, and storing the token.

```python
from kroger_api.auth import authenticate_user

kroger = authenticate_user(scopes="cart.basic:write profile.compact")
```

## PKCE

PKCE (Proof Key for Code Exchange) protects the authorization-code flow from interception with a one-time code verifier and challenge. Kroger authorization endpoints support this in API version 1.0.17. Use it for any application running on devices you do not control.

```python
from kroger_api.utils import generate_pkce_parameters

pkce = generate_pkce_parameters()
# Pass pkce["code_challenge"] with the authorization request,
# then pkce["code_verifier"] with the token exchange.
```

See `examples/oauth_pkce_flow.py` in the repository for the complete flow.

## Switching flows in one script

You can use user auth for the cart and client credentials for lookups without discarding the user's token. The library handles the swap:

```python
from kroger_api.auth import authenticate_user, switch_to_client_credentials

kroger = authenticate_user(scopes="cart.basic:write profile.compact")
kroger, user_token_info, user_token_file = switch_to_client_credentials(
    kroger, scope="product.compact"
)
# ...do lookups, then restore the user token to write to the cart.
```
