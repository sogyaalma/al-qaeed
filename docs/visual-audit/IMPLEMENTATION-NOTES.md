# Phase 2 — Implementation Notes (Application of the Visual Audit)

المرحلة الثانية: تطبيق تحسينات التدقيق البصري على الموقع — ملخص تنفيذي موجز.
المعايير المرجعية: `FINDINGS-REGISTER.md` (F-01…F-25) + `DESIGN-DIRECTIONS.md` (الاتجاه B — Contemporary Premium، بانضباط).

## Files touched (source of truth only — no vendor edits)

| File | What changed |
|---|---|
| `assets/css/theme.css` | All visual refinements as scoped `.alq-*` / `.alq-site` overrides, each block commented with its F-ID. Green-charcoal dark palette (F-24), hero band + portrait plate + type scale + measure + TOC chips + compact publications + stepper dots + tag wrap + equal mobile CTAs + date `bdi` support + footer strip. |
| `tools/build.py` | F-14/17: `DATE_RANGE` regex wraps `\d{4}–\d{4[هـ]` as `<bdi dir="ltr" class="alq-date">` (8 wraps per language). F-12: `prefers-color-scheme` fallback in `THEME_BOOT` (stored preference wins). F-07: hero title+tagline as `.alq-role` + `.alq-tagline` one statement. F-05: EN surname nowrap. F-23: switcher label `data-hidden="sr"`. F-21: first community card `.alq-featured`. F-13: 404 art `/assets/img/404-mark.svg` + labels. CSP hashes regenerate automatically (`write_csp()`). |
| `assets/img/404-mark.svg` | New project-owned brand mark (404 numeral + arch motif + gold rule). Decorative (`alt=""`). |

## Findings → implementation map

- **F-01** tags wrap (`.alq-tags .nds-label` un-clipped) · **F-02** `text-wrap: balance` + AR `word-break: keep-all` · **F-03** equal full-width hero CTAs ≤700px · **F-04** `[lang=ar] { letter-spacing: 0 }` · **F-05** type scale `h1 clamp(1.75rem, 1.1rem+2.2vw, 3.25rem)` (mobile 28px) · **F-06/F-20** measure 36em AR / 34em EN · **F-07** single hero statement on a deep-green identity band · **F-08/F-19** portrait plate 5:6, `clamp(148→232px)` via documented `--avatar-size` knob, `object-position: 52% 18%`, gold hairline (same photo asset, framing only) · **F-09** publications as compact rows · **F-10** TOC chip strip ≤900px (wraps — all 8 links stay visible/clickable at 375px) · **F-11** header slogan hidden ≤640px · **F-12** system dark preference with stored-pref precedence · **F-13** branded 404 + relabeled buttons · **F-14/F-17** Hijri/date ranges isolated in `<bdi dir="ltr">` · **F-15** stepper dots filled · **F-16** single-column contact card · **F-21** featured first community card (gold hairline) · **F-22** `updated_note` as quiet centered footer strip · **F-23** un-clipped switcher label · **F-24** green-charcoal dark palette (verified: axe 0 violations) · **F-25** training rows with dividers.

## Design direction B (restrained)

One memorable moment — the hero: deep-green identity band (`#0a3d32` light / `#0f231c` dark), editorial portrait plate, display name, role + tagline as one statement, one solid CTA + two ghost actions. Gold (`#b08a4f`) appears only as: primary-CTA details, plate hairline, 404 rule, featured-card hairline. Rest of page keeps the paper-green NDS identity untouched.

## Verification (2026-10-18)

| Gate | Result |
|---|---|
| `tests/run_checks.py` (browser, 328 checks: axe 0, TOC-8@375, no overflow @11 widths, 24px targets, 200% text, print, no-JS) | **328/328 ✅** |
| `tests/run_static_checks.py` | **68/68 ✅** |
| `python -m unittest discover -s tests` | **15/15 ✅** |
| `npm run validate` (html-validate) | **PASS ✅** |

After-state screenshots: `evidence/after/` (hero AR/EN @1440/390/768, stepper, publications, TOC chips, dark theme, 404, no-JS).
Hard rules held: no NDS vendor file edited (`docs/nds-assets.json` hashes unchanged), content facts/translations unchanged, portrait file untouched (CSS framing only), no commit/push/deploy.
