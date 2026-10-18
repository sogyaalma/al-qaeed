# NDS findings — cookie deletion on non-domain hosts

- Runtime banner: `1.12.x-dev`; instruction version: NDS IQ 3.1.
- Component: `NDS.Cookies`, eagerly loaded core utility, not consent UI.
- Browser: Firefox 157.0 (Playwright 1.64.0, Linux).
- Observed on a clean browser context at an IPv4 origin: repeated rejected-domain
  cookie warnings for `_ga`, `_gid`, `_gat`, `_fbp`, `_fbc`, without any analytics
  library being installed. Chromium and WebKit did not report equivalent errors.
- Generic reproduction: serve the runtime and minimal NDS page at
  `http://127.0.0.1:8000/`, leave consent unset, collect console messages on load.
- Relevant reviewed source: `_js/nds-cookies.js`, `del()` / eager `apply()`,
  upstream commit `0da6366911e039d5f1afd749a9b116e67dade15d`. The parent-domain loop
  uses `location.hostname.split('.')`, including invalid IP suffixes; the source
  comment also expects browsers to ignore public suffixes. This supporting source
  is not proof of the inherited full bundle's exact compilation commit.
- Scope: noisy local-origin cookie cleanup, not evidence of a tracker or data
  leak. Avoid treating IP segments as parent domains; review public-suffix
  handling upstream separately. Do not grant optional tracking consent to silence
  the messages and do not patch minified bundles or weaken console assertions.
- Host tests use a `localhost` hostname, with console/network assertions retained.
  This is a test-origin correction, **not** an upstream fix or proof of Firefox
  behavior on every public suffix. Real Safari/manual AT are separate checks.

Pending: approved upstream/runtime change if fixing this inside NDS is desired.
No upstream issue was filed and no runtime upgrade was made automatically.
