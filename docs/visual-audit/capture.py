#!/usr/bin/env python3
"""Phase-2 visual-audit capture script (audit tooling — not part of the site build).

Renders the locally packaged site (tools/serve.py on :8000) in real Chromium and
writes screenshots + computed measurements into docs/visual-audit/evidence/.

Usage:
  LD_LIBRARY_PATH=/tmp/al2023/lib \
  CHROMIUM_EXECUTABLE_PATH=/tmp/chromium \
  .venv/bin/python docs/visual-audit/capture.py [base_url]

Outputs are evidence only; nothing here is deployed (package.py excludes docs/).
"""
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "evidence"
EVID.mkdir(parents=True, exist_ok=True)
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
EXECUTABLE = os.environ.get("CHROMIUM_EXECUTABLE_PATH", None)

PAGES = {"ar": "/", "en": "/en/"}
WIDTHS = [1920, 1440, 1280, 1024, 768, 390, 360]
FULL_WIDTHS = [1440, 390]
HEIGHT = 900

measurements = {"base": BASE, "browser": None, "pages": {}}


def ready(page, path):
    resp = page.goto(BASE + path, wait_until="networkidle")
    page.wait_for_function("document.documentElement.hasAttribute('data-nds-loaded')",
                           timeout=15000)
    page.evaluate("document.fonts.ready")
    return resp


def shot(page, name, full=False):
    path = EVID / name
    page.screenshot(path=str(path), full_page=full)
    print("saved", name, flush=True)


def collect_metrics(page, lang, width):
    js = r"""
    () => {
      const cs = (el) => {
        if (!el) return null;
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return {
          fontFamily: s.fontFamily, fontSize: s.fontSize, lineHeight: s.lineHeight,
          fontWeight: s.fontWeight, letterSpacing: s.letterSpacing,
          textAlign: s.textAlign, color: s.color, backgroundColor: s.backgroundColor,
          width: Math.round(r.width), height: Math.round(r.height),
          x: Math.round(r.x), y: Math.round(r.y)
        };
      };
      const paras = Array.from(document.querySelectorAll('.nds-info-content p, #about p'))
        .map(p => {
          const s = getComputedStyle(p);
          const r = p.getBoundingClientRect();
          const text = (p.textContent || '').trim();
          return { chars: text.length, width: Math.round(r.width),
                   fontSize: s.fontSize, lineHeight: s.lineHeight,
                   textAlign: s.textAlign,
                   approxCharsPerLine: text.length && r.width
                     ? Math.round(text.length / Math.max(1, r.height / parseFloat(s.lineHeight)))
                     : null };
        });
      const bgs = {};
      for (const [k, sel] of Object.entries({
          body: 'body', header: 'header .nds-main-nav', hero: '#top',
          subhero: '.nds-sub-hero, .nds-hero-section', content: '#main-content',
          footer: 'footer.nds-footer', card: '.nds-card'})) {
        const el = document.querySelector(sel);
        if (el) bgs[k] = getComputedStyle(el).backgroundColor;
      }
      const overflow = document.documentElement.scrollWidth - innerWidth;
      const lineCounts = paras.map(p => p.approxCharsPerLine);
      return {
        dir: document.documentElement.dir, lang: document.documentElement.lang,
        overflow,
        scrollHeight: document.documentElement.scrollHeight,
        h1: cs(document.querySelector('h1')),
        h2: cs(document.querySelector('h2.nds-section-title')),
        h3: cs(document.querySelector('h3, .nds-block-title')),
        bodyP: cs(document.querySelector('.nds-info-content p')),
        label: cs(document.querySelector('.nds-label')),
        cardTitle: cs(document.querySelector('.nds-card-title')),
        navLink: cs(document.querySelector('.nds-nav-link .nds-label')),
        button: cs(document.querySelector('.nds-btn')),
        toc: cs(document.querySelector('.nds-sideinfo')),
        avatar: (() => { const img = document.querySelector('.alq-hero-avatar img, #top img');
          if (!img) return null; const r = img.getBoundingClientRect();
          const s = getComputedStyle(img);
          return {w: Math.round(r.width), h: Math.round(r.height),
                  naturalW: img.naturalWidth, naturalH: img.naturalHeight,
                  objectFit: s.objectFit, borderRadius: s.borderRadius,
                  src: img.currentSrc || img.src}; })(),
        heroRow: cs(document.querySelector('#top .nds-section-body, #top')),
        backgrounds: bgs,
        paras: paras.slice(0, 6),
        maxApproxCharsPerLine: lineCounts.length ? Math.max(...lineCounts.filter(Boolean)) : null
      };
    }
    """
    metrics = page.evaluate(js)
    measurements["pages"].setdefault(lang, {})[str(width)] = metrics


with sync_playwright() as p:
    opts = {"executable_path": EXECUTABLE} if EXECUTABLE else {}
    browser = p.chromium.launch(**opts)
    measurements["browser"] = browser.version
    print("browser:", browser.version, flush=True)

    # ---- A. viewport tops + full pages, both languages ----
    for lang, path in PAGES.items():
        for width in WIDTHS:
            ctx = browser.new_context(viewport={"width": width, "height": HEIGHT},
                                      reduced_motion="no-preference")
            page = ctx.new_page()
            ready(page, path)
            shot(page, f"home-{lang}-{width}-top.png")
            collect_metrics(page, lang, width)
            if width in FULL_WIDTHS:
                shot(page, f"home-{lang}-{width}-full.png", full=True)
            ctx.close()

    # ---- B. interaction / state captures ----
    for lang, path in PAGES.items():
        # mobile nav open
        ctx = browser.new_context(viewport={"width": 390, "height": HEIGHT})
        page = ctx.new_page()
        ready(page, path)
        page.locator(".nds-nav-toggler button, .nds-main-nav button[aria-controls='nds-nav-collapse']").first.click()
        page.wait_for_timeout(500)
        shot(page, f"home-{lang}-390-nav-open.png")
        ctx.close()

        # footer bottom (desktop + mobile)
        for width in (1440, 390):
            ctx = browser.new_context(viewport={"width": width, "height": HEIGHT})
            page = ctx.new_page()
            ready(page, path)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)
            shot(page, f"home-{lang}-{width}-footer.png")
            ctx.close()

        # mid-page scroll (experience stepper) desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        page = ctx.new_page()
        ready(page, path)
        page.locator("#experience").scroll_into_view_if_needed()
        page.wait_for_timeout(900)
        shot(page, f"home-{lang}-1440-section-experience.png")
        # TOC scrollspy active state after click
        page.locator(".nds-toc a[href='#publications']").click()
        page.wait_for_timeout(1200)
        shot(page, f"home-{lang}-1440-toc-active.png")
        ctx.close()

        # focus state: skip link (keyboard)
        ctx = browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        page = ctx.new_page()
        ready(page, path)
        page.keyboard.press("Tab")
        page.wait_for_timeout(300)
        shot(page, f"home-{lang}-1440-focus-skiplink.png")
        ctx.close()

        # hover state on primary CTA
        ctx = browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        page = ctx.new_page()
        ready(page, path)
        btn = page.locator("#top a.nds-btn.nds-primary, #top a.nds-btn").first
        btn.hover()
        page.wait_for_timeout(300)
        shot(page, f"home-{lang}-1440-hover-cta.png")
        # share dropmenu open
        share = page.locator("button.nds-dropmenu-trigger")
        if share.count():
            share.first.click()
            page.wait_for_timeout(500)
            shot(page, f"home-{lang}-1440-share-open.png")
        ctx.close()

        # stored dark theme (no toggle exists in UI)
        ctx = browser.new_context(viewport={"width": 1440, "height": HEIGHT})
        page = ctx.new_page()
        page.add_init_script("localStorage.setItem('nds-theme','dark')")
        ready(page, path)
        shot(page, f"home-{lang}-1440-dark-top.png")
        collect_metrics(page, lang, "1440-dark")
        ctx.close()

        # no-JS mobile + desktop
        for width in (390, 1440):
            ctx = browser.new_context(viewport={"width": width, "height": HEIGHT},
                                      java_script_enabled=False)
            page = ctx.new_page()
            resp = page.goto(BASE + path, wait_until="load")
            page.wait_for_timeout(800)
            shot(page, f"home-{lang}-{width}-nojs-top.png")
            ctx.close()

        # 200% text resize
        ctx = browser.new_context(viewport={"width": 390, "height": HEIGHT})
        page = ctx.new_page()
        ready(page, path)
        page.evaluate("document.documentElement.style.fontSize='200%'")
        page.wait_for_timeout(400)
        shot(page, f"home-{lang}-390-text-200.png")
        over = page.evaluate("document.documentElement.scrollWidth-innerWidth")
        measurements["pages"].setdefault(lang, {})["text200-overflow-390"] = over
        ctx.close()

    # ---- C. 404 page (Arabic default + EN hash link target) ----
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": HEIGHT})
        page = ctx.new_page()
        resp = page.goto(BASE + "/missing/visual-audit/", wait_until="networkidle")
        page.wait_for_timeout(600)
        measurements.setdefault("status404", []).append(
            {"width": width, "status": resp.status if resp else None})
        shot(page, f"notfound-ar-{width}-top.png")
        ctx.close()

    browser.close()

(ROOT / "evidence" / "measurements.json").write_text(
    json.dumps(measurements, ensure_ascii=False, indent=1), encoding="utf-8")
print("measurements written", flush=True)
