---
sidebar_position: 0
title: Introduction
description: "Documentation for kroger-api (Python client) and kroger-mcp (MCP server): tutorials, how-to guides, concepts, and reference for building on the Kroger Public API."
slug: /
---

# Kroger Python API Toolkit

This documentation is for two unofficial, open-source Python packages that build on the [Kroger Public API](https://developer.kroger.com/):

- **[kroger-api](https://github.com/CupOfOwls/kroger-api)** is a Python client. It handles authentication via client credentials, authorization code, and PKCE. It also covers locations, products, carts, and identity, while managing token storage and refresh automatically.
- **[kroger-mcp](https://github.com/CupOfOwls/kroger-mcp)** is a [Model Context Protocol](https://modelcontextprotocol.io/) server built on kroger-api. It lets AI assistants use these capabilities as tools, with a human (optionally) approving each tool call.

Kroger is a family of grocery banners across the United States. The Public API reaches stores and products across banners including Kroger, Ralphs, King Soopers, City Market, Fred Meyer, QFC, Fry's, Smith's, Dillons, Baker's, Gerbes, Harris Teeter, Mariano's, Pick 'n Save, Metro Market, JayC, Pay Less, Ruler Foods, Food 4 Less, and Foods Co.

## Where to start

| You want to...                                               | Go to                                                                        |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Make your first API call and end with an item in a real cart | [Tutorial: Use the Kroger API in Python](get-started/use-the-kroger-api.mdx) |
| Give an AI assistant grocery capabilities                    | [Lab: Build an AI agent with kroger-mcp](building-ai-agents/agent-lab.mdx)   |
| Solve a specific task (auth flows, refresh, rate limits)     | [How-to guides](how-to/choose-an-auth-flow.md)                               |
| Understand how the client is put together                    | [Concepts](concepts/client-architecture.md)                                  |
| Look something up                                            | [Reference](reference/mcp-tools.md)                                          |
