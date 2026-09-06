---
sidebar_position: 3
title: Changelog and versions
description: "Where releases are recorded for kroger-api and kroger-mcp, and the versioning scheme both packages follow."
---

# Changelog and versions

Both packages follow [Semantic Versioning](https://semver.org/) and keep a [Keep a Changelog](https://keepachangelog.com/)-format `CHANGELOG.md` at the repository root, with community contributions credited by pull request number.

- **kroger-api**: [CHANGELOG.md](https://github.com/CupOfOwls/kroger-api/blob/main/CHANGELOG.md) · [releases](https://github.com/CupOfOwls/kroger-api/releases) · [PyPI](https://pypi.org/project/kroger-api/)
- **kroger-mcp**: [CHANGELOG.md](https://github.com/CupOfOwls/kroger-mcp/blob/main/CHANGELOG.md) · [releases](https://github.com/CupOfOwls/kroger-mcp/releases) · [PyPI](https://pypi.org/project/kroger-mcp/)

## Upstream API versions

kroger-api vendors the Kroger Public API's OpenAPI specifications it was built against under `docs_kroger_api/` in the repository. The client passes raw JSON through, so new upstream response fields (such as the nutrition data added in Products 1.3.0) are available without a client release.
