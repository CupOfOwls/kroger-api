# Instructions for AI agents editing these docs

Condensed, imperative tier of the documentation style guide. The full guide with
reasoning is `docs/contributing/style-guide.md`; do not load it unless a task
needs a rule not covered here. Keep all three tiers (full guide, cheat sheet,
this file) in sync: a PR that changes one updates the others.

## Content types

- Each page is exactly one of: tutorial, how-to, reference, explanation. The
  sidebar section says which. Never mix.
- Tutorials: single path, no alternatives, no inline branches. Move branches to
  a how-to page and link from "Next steps."
- Tutorials carry: 3–4 measurable objectives (action verbs, never
  "understand"), one interactive knowledge check per major step (the `Quiz`
  component: reader commits before feedback; feedback narrates the
  consequence, never says only "Incorrect"), and a capstone chaining the
  objectives. No alignment table on the page; put the objective→check mapping
  in the PR description.

## Writing rules

- Second person, active voice, present tense. American spelling. Oxford comma.
- Sentence-case headings, descriptive, no trailing colon, never "Overview."
- Bold for UI elements and file names in steps; code font for commands,
  parameters, values, paths. Tables for anything list-shaped.
- Numbered lists: `1.` for every item in source.
- Admonitions note/warning/tip only, never stacked, never holding a required step.
- No em dashes, no "simply/just/easy/please," no exclamation marks in steps.
- Spell out one–nine; numerals for 10+ and all versions, prices, units.
- Internal links: relative, `.md` extension, descriptive text.
- Terminology: OAuth; Kroger API; `kroger-api` and `kroger-mcp` in code font
  lowercase; access token; rate limit; ZIP code.
- Sections self-contained (no "as mentioned above"); first sentence of each
  section says what it is; no value only in an image; code fences complete and
  language-tagged.

## Checks before proposing changes

- `npm run build` must pass (broken internal links fail the build).
- Prettier formats all Markdown: `npx prettier --check .`
- Vale lints prose: `vale docs/` (advisory; fix errors, use judgment on
  suggestions).
