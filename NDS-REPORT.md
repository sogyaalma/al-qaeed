# NDS findings

Instruction version: NDS IQ 3.1. Findings only; no project routes or content.

## Cookie deletion on non-domain hosts

- Runtime banner at observation: `1.12.x-dev`.
- Component: `NDS.Cookies`, eagerly loaded core utility, not consent UI.
- Browser: Firefox 157.0 (Playwright 1.64.0, Linux).
- Observed on a clean browser context at an IPv4 origin: repeated rejected-domain cookie warnings for `_ga`, `_gid`, `_gat`, `_fbp`, `_fbc`, without any analytics library being installed. Chromium and WebKit did not report equivalent errors.
- Generic reproduction: serve the runtime and a minimal NDS page at `http://127.0.0.1:8000/`, leave consent unset, collect console messages on load.
- Relevant reviewed source at the time: `_js/nds-cookies.js`, `del()` / eager `apply()`, upstream commit `0da6366911e039d5f1afd749a9b116e67dade15d`. The parent-domain loop uses `location.hostname.split('.')`, including invalid IP suffixes.
- Scope: noisy local-origin cookie cleanup, not evidence of a tracker or data leak. Do not grant optional tracking consent to silence the messages and do not patch minified bundles.
- Host tests use a `localhost` hostname. That is a test-origin correction, not an upstream fix.

Status on 2026-11-01: the served runtime is now tag v1.12.0 @ `030d1c7ff4ab5a3092c17b93429b1ac55291ea4d` (banner `1.12.0`). This cookie observation was **not** re-run against those bundles (no browser in the pin environment). Do not treat the pin as a fix, and do not treat the old observation as proof about v1.12.0.

## Findings against tag v1.12.0

1. **No OS-preference surface.** `NDS.Theme` persists a manual `data-theme` choice under `localStorage` key `nds-theme`. `components/themes.md` documents the toggle and persistence. It does not read `prefers-color-scheme`. A consumer that needs the OS preference has to add it outside the canonical head script.
2. **`nds-purple` is used and not shipped.** `_data/content/faqs.yml` applies `nds-purple`. `_tags.scss` in this tag ships blue, gray, green, neutral, red, and yellow only. The class has no rule.
3. **Comment points at a missing file.** `_sass/themes/_register.scss` refers to `themes/_foundation-day.scss`. That file is not in the tag.
4. **Accessibility fieldset has no legend.** `_includes/accessibility-panel.html` wraps the mode switches in `<fieldset class="nds-form-group nds-switch-group">` and does not include a `<legend>` (WCAG 2.1 H71).
5. **Progress ring is a `div` inside a `button`.** The same panel wraps `.nds-progress-circle` in a `<div>`. `_sass/components/_buttons.scss` styles the class, not the element name, so the content model does not depend on `div`.
6. **Docs-only demo hooks.** `nds-showcase.min.js` is not in `assets/js/` of the tag. Documented attributes such as `data-goto` and `data-sort-key` are read by that docs script only. They are inert under the runtime bundles.
