---
sidebar_position: 2
title: How MCP approval and scopes work
description: "The two-layer permission model when an AI agent uses kroger-mcp: OAuth scopes bound the server, human approval bounds each call."
---

# How MCP approval and scopes work

Two independent permission layers separate the model from your Kroger account when an AI assistant uses [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp). The [lab](../building-ai-agents/agent-lab.mdx) exercises both.

## Layer 1: OAuth scopes

The server authenticates to Kroger the same way any kroger-api script does, using the same flows and scopes. If a server has only run the client-credentials flow, it can search stores and products. It cannot do anything else, regardless of what an agent asks for. Cart writes exist only after a human completes the sign-in flow (run through the server's `start_authentication` and `complete_authentication` tools) and grants `cart.basic:write`.

The model does not hold credentials. The `claude_desktop_config.json` env block provides the client ID and secret to the _server process_. The model only interacts via tool calls.

## Layer 2: per-call approval

By default, every tool call pauses for human approval in the client UI (clients let you mark tools as always allowed). This catches actions that are technically correct but unwanted: if you ask an agent to find milk and it decides to buy it, the cart write shows up for approval. You can deny it, and the agent sees the refusal and re-plans.

The layers cover different failures. Scopes are coarse and durable: you set them once, and it is hard to widen them by accident. Approval judges one call at a time. An agent acting inside scope but against your intent gets caught at approval time, and if you are tricked into approving a call, the granted scopes still limit what it can do.

## What this means in practice

- Read tools for locations, products, chains, and departments carry `Auth Required: No` in the [tool reference](../reference/mcp-tools.md). These use the client-credentials token and require little scrutiny for approval.
- Cart tools marked `Auth Required: Yes` interact with real accounts. Review these approvals carefully.
- kroger-mcp maintains a local-only cart record (`view_current_cart`, order history). This lets the agent track intent without writing to an account, so a shopping session can proceed with no cart writes at all.
