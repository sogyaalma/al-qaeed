Managed by NDS IQ

Runtime: NDS Vanilla v1.12.0, commit 030d1c7ff4ab5a3092c17b93429b1ac55291ea4d, banner 1.12.0. Provenance in docs/nds-assets.json. Instruction version: NDS IQ 3.1 (matches main on 2026-11-01; tag IQv3.2 was not installed).
Asset URL prefix: `/assets/`
Porting strategy: in-place rebuild of the design-system layer. Content JSON, routes, and the Cloudflare packaging model were kept.
Prior NDS: inherited 1.12.x-dev bundles, treated as non-conformant and replaced. Not used as a markup source.
CSP: present. Head inline scripts are hashed. No authored `style=` attributes. `style-src-attr 'unsafe-inline'` remains because NDS components set style properties at runtime.
Government chrome: not shipped on the biography. The showcase names the digital-stamp example and does not reproduce it.
Pacing: whole plan.
Built twin: absent. The release ZIP host is unreachable from this environment, so no `_site` visual comparison was possible.

| Page | Route | Legacy libraries | NDS target | Status |
|---|---|---|---|---|
| Arabic biography | `/` | none (vanilla HTML/CSS/JS) | faculty-cv + page-shell + hero-sub + toc + footer | In Progress |
| English biography | `/en/` | none | same as `/` | In Progress |
| 404 | `/404.html` | none | 404-template status section | In Progress |
| Component showcase | `/nds-showcase/` | none | catalog of the pinned tag, live components, noindex | In Progress |

Rows stay In Progress. Agent-owned static checks passed, but browser verification of this rebuild has not been run here, the built twin is absent, and only the owner can set Built and Verified.

- [x] Asset URL prefix `/assets/`
- [x] In-place rebuild of the design-system layer
- [x] Pin v1.12.0 after checking it is the latest stable release
- [x] Replace DGA stamp / government wording on the biography
- [x] Move CSP knobs to project classes; brand seeds use the documented palette engine
- [x] Showcase route covers the pinned catalog and labels gaps
- [ ] Browser verification of this rebuild (Chromium, Firefox, WebKit, axe, no-JS, print, dark, 200% text). The workflow runs it; it was not run in the implementation environment.
- [ ] `_site` visual-twin comparison, blocked on the release ZIP.
- [ ] Owner confirmation of the plan, publication, and asset rights.
