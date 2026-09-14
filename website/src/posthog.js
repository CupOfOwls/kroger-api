// PostHog product analytics — a Docusaurus client module.
//
// Cookieless by design: PostHog dedupes daily visits with a rotating server-side
// hash of IP + user agent and stores nothing on the visitor's device (no cookie,
// no local storage, no session recording). A short privacy note lives at
// /kroger-api/analytics-and-privacy.
//
// The token below (phc_...) is a PUBLIC, write-only ingest key — safe to commit;
// it cannot read any data back. The personal (phx_...) key is never in this repo.
//
// Single pageview source: posthog-js auto-pageview is OFF; we fire $pageview on
// each Docusaurus route change (below), so single-page-app navigations are
// counted once, without the double-counting that on-by-default pageviews cause.
//
// Autocapture is OFF (no per-click $autocapture noise); instead we fire a few
// hand-picked, low-cardinality events for the actions that actually signal
// engagement — outbound clicks to GitHub/PyPI/the Kroger portal, code-copy
// button presses, and quiz answers (see components/Quiz).
//
// ONE-TIME PROJECT SETTING (required): turn ON "Cookieless server hash mode"
// under PostHog → Project settings → Web analytics, or cookieless events are
// silently dropped.
import ExecutionEnvironment from "@docusaurus/ExecutionEnvironment";
import siteConfig from "@generated/docusaurus.config";
import posthog from "posthog-js";

// Bucket an outbound host into a short, stable label so a breakdown reads as
// "github / pypi / kroger-portal / other" instead of a pile of raw hostnames.
function destinationOf(hostname) {
  if (/(^|\.)github\.com$/.test(hostname)) return "github";
  if (/(^|\.)pypi\.org$/.test(hostname)) return "pypi";
  if (/(^|\.)developer\.kroger\.com$/.test(hostname)) return "kroger-portal";
  if (/(^|\.)modelcontextprotocol\.io$/.test(hostname)) return "mcp-spec";
  if (/(^|\.)posthog\.com$/.test(hostname)) return "posthog";
  return "other";
}

// One delegated, capture-phase listener for the whole document handles both
// outbound-link and code-copy tracking without touching per-component code.
function trackInteractions() {
  document.addEventListener(
    "click",
    (event) => {
      if (!posthog.__loaded) return;
      const target = event.target;
      if (!target || !target.closest) return;

      // Docusaurus renders a copy button on every code block; its aria-label
      // starts with "Copy". Report which page and language got copied.
      const copyBtn = target.closest('button[aria-label^="Copy"]');
      if (copyBtn) {
        // Docusaurus puts the `language-xxx` class on the block CONTAINER and
        // the <pre>, not on <code>. Read it from whichever carries it.
        const container = copyBtn.closest(
          '[class*="codeBlockContainer"], [class*="theme-code-block"]',
        );
        const pre = container && container.querySelector("pre");
        const classes = [container, pre]
          .map((el) => (el && el.className ? el.className.toString() : ""))
          .join(" ");
        const lang = (classes.match(/language-([\w-]+)/) || [])[1] || "unknown";
        posthog.capture("code_copy", {
          page: window.location.pathname,
          language: lang,
        });
        return;
      }

      // Outbound links: anything that resolves to a different origin.
      const link = target.closest("a[href]");
      if (!link) return;
      let url;
      try {
        url = new URL(link.href);
      } catch {
        return;
      }
      if (url.origin === window.location.origin) return; // internal nav is a $pageview
      if (url.protocol !== "http:" && url.protocol !== "https:") return; // skip mailto:, etc.
      posthog.capture("outbound_click", {
        href: url.href,
        host: url.hostname,
        destination: destinationOf(url.hostname),
        text: (link.textContent || "").trim().slice(0, 100),
        page: window.location.pathname,
      });
    },
    { capture: true },
  );
}

if (ExecutionEnvironment.canUseDOM) {
  const { posthogKey, posthogHost } = siteConfig.customFields || {};
  if (posthogKey) {
    posthog.init(posthogKey, {
      api_host: posthogHost,
      cookieless_mode: "always", // server-side daily hash; nothing stored on device
      capture_pageview: false, // fired manually on route change (single source)
      disable_session_recording: true, // never record docs readers
      autocapture: false, // no noisy per-click $autocapture events
      capture_heatmaps: true, // aggregate click/rage/dead-click heatmaps (cookieless-compatible)
      respect_dnt: true,
    });
    // Expose the instance so the PostHog toolbar (heatmap/action authoring) and
    // browser-console debugging can reach it, as the standard snippet install does.
    window.posthog = posthog;
    trackInteractions();
  }
}

// Docusaurus calls this on the first load and every client-side navigation.
export function onRouteDidUpdate({ location, previousLocation }) {
  if (!ExecutionEnvironment.canUseDOM) return;
  if (previousLocation && location.pathname === previousLocation.pathname) return;
  if (posthog.__loaded) posthog.capture("$pageview");
}
