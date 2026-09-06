// Journey-shaped IA: start → build with AI → task recipes → concepts → reference.
// Content types stay separated: tutorials teach on a single path, how-to guides
// hold the branches, reference describes, concepts explain.

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    "index",
    {
      type: "category",
      label: "Get started",
      collapsed: false,
      items: ["get-started/use-the-kroger-api"],
    },
    {
      type: "category",
      label: "Building AI agents",
      collapsed: false,
      items: ["building-ai-agents/agent-lab"],
    },
    {
      type: "category",
      label: "How-to guides",
      items: [
        "how-to/choose-an-auth-flow",
        "how-to/refresh-tokens",
        "how-to/handle-rate-limits",
      ],
    },
    {
      type: "category",
      label: "Concepts",
      items: ["concepts/client-architecture", "concepts/mcp-approval"],
    },
    {
      type: "category",
      label: "Reference",
      items: [
        "reference/mcp-tools",
        "reference/glossary",
        "reference/changelog",
      ],
    },
    {
      type: "category",
      label: "Contributing",
      items: ["contributing/style-guide", "contributing/style-cheatsheet"],
    },
  ],
};

module.exports = sidebars;
