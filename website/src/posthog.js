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
// ONE-TIME PROJECT SETTING (required): turn ON "Cookieless server hash mode"
// under PostHog → Project settings → Web analytics, or cookieless events are
// silently dropped.
import ExecutionEnvironment from "@docusaurus/ExecutionEnvironment";
import siteConfig from "@generated/docusaurus.config";
import posthog from "posthog-js";

if (ExecutionEnvironment.canUseDOM) {
  const { posthogKey, posthogHost } = siteConfig.customFields || {};
  if (posthogKey) {
    posthog.init(posthogKey, {
      api_host: posthogHost,
      cookieless_mode: "always", // server-side daily hash; nothing stored on device
      capture_pageview: false, // fired manually on route change (single source)
      disable_session_recording: true, // never record docs readers
      respect_dnt: true,
    });
  }
}

// Docusaurus calls this on the first load and every client-side navigation.
export function onRouteDidUpdate({ location, previousLocation }) {
  if (!ExecutionEnvironment.canUseDOM) return;
  if (previousLocation && location.pathname === previousLocation.pathname) return;
  if (posthog.__loaded) posthog.capture("$pageview");
}
