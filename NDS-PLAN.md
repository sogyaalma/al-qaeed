Managed by NDS IQ

Runtime: NDS Vanilla 1.12.x-dev (compiled from mazin-musleh/NDS-vanilla `main`).
Asset URL prefix: `/assets/`
Porting strategy: in-place rebuild (explicit request to recreate the site with NDS-vanilla).
Prior NDS: none in the served UI.
CSP: present. Blocking stylesheets; no inline `style=` knobs (moved to `assets/css/theme.css`).
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
- [ ] Browser verification (`NDS.Init.audit()`, desktop + mobile screenshots)
