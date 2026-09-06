---
sidebar_position: 1
title: Documentation style guide
description: "The writing standards for these docs: voice, structure, formatting, terminology, and the content-type discipline that keeps pages doing one job."
---

# Documentation style guide

This guide governs everything published on this site. It exists in three tiers so every kind of contributor gets the right amount of it:

1. **This page**: the full guide, with reasoning, for anyone writing or reviewing docs.
1. **[The cheat sheet](style-cheatsheet.md)**: the same rules compressed to a scan-in-one-minute table.
1. **`website/AGENTS.md`** in the repository: a condensed, imperative version for AI coding agents, so an agent editing these docs follows the same rules without loading this whole page into context.

When this page changes, update the other two tiers in the same pull request.

## Content types: one page, one job

Every page is exactly one of four kinds, and the sidebar section it lives in says which:

| Kind         | Job                                         | Lives in                        | Register                       |
| ------------ | ------------------------------------------- | ------------------------------- | ------------------------------ |
| Tutorial     | Teach, on a single path, with no choices    | Get started, Building AI agents | "In this tutorial, we will…"   |
| How-to guide | Solve one real-world task, branches allowed | How-to guides                   | Imperative, assumes competence |
| Reference    | Describe, completely and neutrally          | Reference                       | Tables, austere                |
| Explanation  | Explain why, discursively                   | Concepts                        | Essay-like, opinions allowed   |

The most common failure is a tutorial sprouting how-to branches ("alternatively, you could…"). Move the branch to a how-to page and link it from the tutorial's **Next steps**, never inline.

Tutorials additionally carry the learning scaffolding this site is built around: 3–4 measurable objectives up front (action verbs such as _apply_, _analyze_, and _create_, never "understand"), one scenario-shaped knowledge check per major step mapped to exactly one objective, and a capstone that chains the objectives. Knowledge checks are interactive: the reader commits to an answer before any feedback appears (the `Quiz` component), and feedback narrates consequences ("the call returns 401 because…") rather than announcing "Incorrect." The objective→check mapping is a design tool; keep it in the pull request description, not on the page.

## Voice and tone

- Second person ("you"), active voice, present tense. "Run the script," not "The script should be run."
- Frame around what the reader can do: "With PKCE, you can distribute the client safely," not "PKCE allows safe distribution."
- Contractions are fine; breeziness is not. No exclamation marks in instructional text.

<!-- vale kroger.NoFiller = NO -->

- No "please" in steps. No "simply," "just," or "easy": if it were, the reader would not be here.

<!-- vale kroger.NoFiller = YES -->

## Formatting

- **Sentence-case headings**, no trailing colon, descriptive and action-oriented ("Refresh tokens automatically," never "Overview").
- **Oxford comma.** American spelling.
- **Bold** for UI elements and file names in instructions; `code font` for commands, parameters, values, and paths in technical context; _italics_ only for word-level emphasis, sparingly.
- Numbered lists use `1.` for every item in source; Markdown renders the sequence.
- Tables, not prose, for anything list-shaped: parameters, tool inventories, rate limits, decision matrices.
- Admonitions: `note`, `warning`, and `tip` only. Never stacked, never containing a required step, because readers skip boxes. Exemption: a prerequisites list may live in a `note`, since it is a gate rather than a step.
- Spell out one through nine; numerals for 10 and up; numerals always for versions, prices, and units.
- No em dashes in docs prose. Shorter sentences instead.

## Links

- Internal links are relative and carry the `.md` extension: `[refresh guide](../how-to/refresh-tokens.md)`.
- Link text says where it goes ("see the [tool reference](../reference/mcp-tools.md)"), never "click here."
- Every claim about the upstream API links to, or names, its source (the vendored OpenAPI specs, the developer portal).

## Terminology

Consistent names, with the terminology table enforced by Vale (see below):

<!-- vale off -->

| Always                                                          | Never                       |
| --------------------------------------------------------------- | --------------------------- |
| OAuth                                                           | Oauth, oauth                |
| Kroger API (the upstream service)                               | Kroger api                  |
| `kroger-api`, `kroger-mcp` (the packages, code font, lowercase) | Kroger-API, KrogerMCP       |
| access token                                                    | Access Token (mid-sentence) |
| rate limit                                                      | ratelimit                   |
| ZIP code                                                        | zip code, zipcode           |

<!-- vale on -->

"AI-ready" writing rules, because these docs are consumed by agents as well as people: every section's first sentence says what the section is; sections are self-contained (no "as mentioned above"); no value the reader needs exists only inside an image; every code fence is complete, runnable where possible, and language-tagged.

## Enforcement

- **Prettier** formats all Markdown, MDX, and config files; it is a hard gate in CI.
- **Vale** enforces the terminology table and a subset of the language rules; it runs in CI on changed lines and comments on the pull request (on fork PRs the comments degrade to log annotations). Vale findings are advisory: a human decides, but decides visibly.
- The Docusaurus build fails on any broken internal link. External links are checked on a schedule.

## Review

Documentation changes get the same review as code changes: a pull request, CI green, and a human read. Reviewers check content-type discipline first (is this page doing one job?), correctness second, and style third; Vale and Prettier have already done most of the third.
