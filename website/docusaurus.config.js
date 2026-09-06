// @ts-check
// Docs site for kroger-api and kroger-mcp.
// Built docs-as-code: Markdown in Git, Prettier formatting, Vale style
// linting in CI, broken links fail the build.

const { themes: prismThemes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Kroger Python API Toolkit",
  tagline:
    "A Python client and MCP server for the Kroger Public API: grocery data, carts, and AI agents",
  favicon: "img/favicon.svg",

  url: "https://cupofowls.github.io",
  baseUrl: "/kroger-api/",
  organizationName: "CupOfOwls",
  projectName: "kroger-api",
  trailingSlash: false,

  // A broken internal link is a build failure, not a warning.
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "throw",

  // Rspack-based build pipeline (Docusaurus "faster" mode).
  future: {
    v4: { removeLegacyPostBuildHeadAttribute: true },
    experimental_faster: true,
  },

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: "./sidebars.js",
          routeBasePath: "/",
          editUrl: "https://github.com/CupOfOwls/kroger-api/tree/main/website/",
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      }),
    ],
  ],

  plugins: [
    [
      "docusaurus-plugin-llms",
      {
        // Generate llms.txt and llms-full.txt for agent/RAG consumption.
        // The two .mdx tutorial pages are excluded: their interactive Quiz
        // components are JSX and do not survive the markdown export.
        generateLLMsTxt: true,
        generateLLMsFullTxt: true,
        generateMarkdownFiles: true,
        addMdExtension: true,
        ignoreFiles: [
          "get-started/use-the-kroger-api.mdx",
          "building-ai-agents/agent-lab.mdx",
        ],
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: "Kroger Python API Toolkit",
        items: [
          {
            type: "docSidebar",
            sidebarId: "docsSidebar",
            position: "left",
            label: "Docs",
          },
          {
            href: "https://github.com/CupOfOwls/kroger-api",
            label: "kroger-api",
            position: "right",
          },
          {
            href: "https://github.com/CupOfOwls/kroger-mcp",
            label: "kroger-mcp",
            position: "right",
          },
        ],
      },
      footer: {
        style: "dark",
        links: [
          {
            title: "Docs",
            items: [
              { label: "Get started", to: "/get-started/use-the-kroger-api" },
              {
                label: "Building AI agents",
                to: "/building-ai-agents/agent-lab",
              },
            ],
          },
          {
            title: "Project",
            items: [
              {
                label: "kroger-api on PyPI",
                href: "https://pypi.org/project/kroger-api/",
              },
              {
                label: "kroger-mcp on PyPI",
                href: "https://pypi.org/project/kroger-mcp/",
              },
              {
                label: "Kroger Developer Portal",
                href: "https://developer.kroger.com/",
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Stephen Thoemmes. MIT licensed.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ["bash", "json", "python"],
      },
    }),
};

module.exports = config;
