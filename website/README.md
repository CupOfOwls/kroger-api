# Docs site

Source for the Kroger Python API Toolkit documentation, built with
[Docusaurus](https://docusaurus.io/).

## Local development

```bash
npm ci
npm start        # live-reload dev server
npm run build    # production build; broken internal links fail it
```

## Contributing

Prose style is governed by the
[style guide](docs/contributing/style-guide.md) (condensed
[cheat sheet](docs/contributing/style-cheatsheet.md); AI-agent tier in
[AGENTS.md](AGENTS.md)). Vale lints prose and Prettier enforces formatting in
CI on every pull request.

Deploys run through GitHub Actions: a push to `main` that touches `website/`
builds the site and publishes it to GitHub Pages. Do not deploy by hand.
