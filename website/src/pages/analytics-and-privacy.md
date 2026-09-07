# Analytics & privacy

This documentation site uses [PostHog](https://posthog.com) to understand which
pages are useful: pageviews, referrers, and which quiz answers readers pick.

It runs in **cookieless** mode. Nothing is stored on your device: no cookies, no
local storage, and no session recording. PostHog dedupes daily visits with a
rotating server-side hash of your IP address and user agent, which it discards
each day. Your IP is processed transiently for that hash and for coarse
geography; it is not stored against you, and no account, email, or personal
profile is collected.

The analytics token embedded in this site's source is a public, write-only key.
It can send events but cannot read any data back.

If you would rather not be counted, an ad or tracker blocker (which blocks
PostHog's domain) or your browser's Do Not Track setting will exclude you.
