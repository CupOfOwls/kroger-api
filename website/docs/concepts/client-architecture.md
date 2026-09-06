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

## MCP system

Authentication, storage, and resource groups are separable. This allows [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp) to wrap each client capability as an MCP tool. The MCP server handles the agent side (tool listing and tool calls) and passes Kroger requests to kroger-api. The [approval model](mcp-approval.md) applies to each call that crosses that boundary.
