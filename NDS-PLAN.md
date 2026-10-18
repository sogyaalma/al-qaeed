Managed by NDS IQ

Runtime: inherited NDS Vanilla 1.12.x-dev artifacts; exact upstream build commit unverified. See docs/NDS-INTEGRATION.md and docs/nds-assets.json.
Asset URL prefix: `/assets/`
Porting strategy: in-place rebuild (explicit request to recreate the site with NDS-vanilla).
Prior NDS: none in the served UI.
CSP: present. Async stylesheet preloads with canonical bootstrap + blocking noscript fallback; no inline `style=` knobs (moved to `assets/css/theme.css`).
Government chrome: not shipped. This is a personal biographical site; NDS disclaimer requires replacing DGA identity before going live.
Pacing: whole plan.

| Page | Route | Legacy libraries | NDS target | Status |
|---|---|---|---|---|
| Arabic biography | `/` | none (vanilla HTML/CSS/JS) | faculty-cv example + page-layout article/sideinfo + hero-profile | In Progress |
| English biography | `/en/` | none | same as `/` | In Progress |
| 404 | `/404.html` | none | 404-template status section | In Progress |

Open:
- [x] Asset URL prefix `/assets/`
- [x] In-place rebuild (user request)
- [x] Replace DGA stamp / Vision 2030 / government logos
- [x] Convert CSP knobs to `.alq-*` classes
- [x] Site browser verification (2026-10-18): awaited `NDS.Init.audit()` zero findings, 328/328 Chromium checks, desktop/mobile screenshots inspected.
- [ ] Matching built `_site` visual-twin comparison / full NDS IQ conformance: exact inherited upstream build unverified.
- [ ] Owner confirmation of NDS plan and publication/asset rights.

Rows remain In Progress because browser success alone does not complete the missing canonical-twin/owner gates. Current evidence: docs/AUDIT-2026-10-18.md.
