---
sidebar_position: 1
title: How kroger-api models the Kroger API
description: "Why the client is organized as resource groups over a shared authenticated client, and how token storage keeps scripts stateless."
---

# How kroger-api models the Kroger API

## Resource groups over a shared client

The Kroger Public API publishes a separate OpenAPI specification per surface, and the client mirrors that structure:

```
KrogerAPI
├── .authorization   # token acquisition and refresh
├── .location        # stores, chains, departments
├── .product         # search and details
├── .cart            # add items (user-authorized)
└── .identity        # user profile (user-authorized)
```

A single `KrogerAPI` instance manages one authenticated HTTP client, and resource groups are views onto it. `switch_to_client_credentials` relies on this: the client's token changes, the resource groups stay, and a script can switch between app and user roles without rebuilding anything.

Upstream OpenAPI specifications are vendored into the repository at `docs_kroger_api/`: the versions the client was built against, plus a snapshot of the current published specs. This means when Kroger adds response fields, such as the 1.3.0 nutrition data, they pass through untouched. The client provides raw JSON instead of filtering responses through models that would drop new fields.

## Tokens as files, scripts as stateless

The client writes every token it obtains to a file, named per flow (and per scope for client-credentials tokens), in a shared data directory (`$KROGER_TOKEN_DIR`, defaulting to the platform data dir such as `~/.local/share/kroger-mcp/`). kroger-api and kroger-mcp read the same directory, so a sign-in done for one is available to the other. This has several effects:

- Scripts are restartable. A rerun loads the stored token instead of prompting you again.
- The browser round-trip occurs once per grant. It does not repeat every time you run the script.
- You can refresh tokens because the refresh token survives the process that obtained it.
- Multiple flows can coexist. User tokens and client-credentials tokens are stored in separate files so they do not overwrite each other.

The token directory is sensitive state on disk. Token files are credentials; the [refresh guide](../how-to/refresh-tokens.md) closes on the same warning: do not commit them.

## Errors carry the response

The Kroger API reports a problem in several ways, depending on which layer handles the request: an error object with a code and reason from the Products and Locations APIs, an OAuth error from the token endpoint, a bare `{"message": "Unauthorized"}` from the API gateway, or an empty body for most `404` responses. An exception that only said "400 Client Error" would discard all of that, so each exception keeps the parsed code and reason, the request, the correlation ID, and the body, and adds a hint where the cause is known. The [errors reference](../reference/errors.md) lists what each one carries.

The exception classes follow HTTP status codes because a caller decides what to do from the status: correct the request after a `400`, sign in again after a `401`, stop after a `429`, and retry after a `5xx`. Each class also derives from the matching `requests` exception, so code written for earlier versions keeps working.

Some mistakes produce no error at all. The Kroger API ignores a `fulfillment` value it does not know, and a location search `limit` of `0`, and returns results that look valid but are not filtered. That is why the client checks arguments before it sends a request: a check is the only place such a mistake can surface. The constraints are public constants, so `kroger-mcp` publishes the same limits in its tool schemas.

## MCP system

Authentication, storage, and resource groups are separable. This allows [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp) to wrap each client capability as an MCP tool. The MCP server handles the agent side (tool listing and tool calls) and passes Kroger requests to kroger-api. The [approval model](mcp-approval.md) applies to each call that crosses that boundary. When a call fails, the server turns the `kroger-api` exception into an MCP [error result](../reference/mcp-tools.md#error-results), with the same details and a next step that names the tool to use, so the agent can correct itself.
