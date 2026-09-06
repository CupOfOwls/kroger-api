---
sidebar_position: 2
title: Glossary
description: "Definitions of Kroger API and MCP terms used throughout these docs: locationId, UPC, modality, scopes, tool calls, and more."
---

# Glossary

**access token**: The short-lived credential (30 minutes) sent with each API request. Obtained through one of the [three auth flows](../how-to/choose-an-auth-flow.md).

**approval loop**: The MCP client behavior of pausing every tool call for explicit human consent. See [How MCP approval and scopes work](../concepts/mcp-approval.md).

**client credentials**: The OAuth2 flow in which the app authenticates as itself, with no user. Grants access to public data only.

**locationId**: The identifier for one specific store. Product prices, availability, and aisle locations only exist relative to a `locationId`.

**modality**: How a cart item will be fulfilled: `PICKUP` or `DELIVERY`.

**MCP (Model Context Protocol)**: An open standard letting AI applications call external tools. kroger-mcp is an MCP server; Claude Desktop and Claude Code are MCP clients.

**PKCE**: Proof Key for Code Exchange; an extension hardening the authorization-code flow with a one-time verifier/challenge pair. Supported by Kroger's authorization endpoints as of version 1.0.17.

**refresh token**: The long-lived credential stored alongside a user access token, used to obtain new access tokens without re-prompting the user. Client-credentials tokens do not carry one.

**scope**: A named permission a token carries, such as `product.compact` (read products) or `cart.basic:write` (modify the cart). Scopes are granted at token time and cannot be widened afterward.

**token file**: The local JSON file where kroger-api persists a token and its refresh token, named for the flow and scopes that produced it. Token files are credentials; never commit them.

**tool call**: One invocation of one MCP tool by the model, subject to the approval loop.

**UPC**: Universal Product Code; the identifier used when adding an item to the cart.
