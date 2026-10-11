#!/usr/bin/env python3
"""
End-to-end checks for the static site. Run while the site is being served:

  python3 -m http.server 8000 --bind 0.0.0.0   (in the project root)
  python3 tests/run_checks.py http://127.0.0.1:8000

Writes screenshots to docs/screenshots/ and a JSON report to docs/test-results.json.
Every result printed here is measured in the browser; nothing is assumed.
"""
import json
import pathlib
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright
import axe_core_python

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
AXE_JS = pathlib.Path(axe_core_python.__file__).parent / "axe.min.js"

WIDTHS = {"360": 360, "768": 768, "1024": 1024, "1440": 1440, "1920": 1920}
PAGES = {"ar": "/", "en": "/en/"}

report = {"checks": [], "failures": 0}


def check(name, ok, detail=""):
    report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)})
    if not ok:
        report["failures"] += 1
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def http_status(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        return err.code, ""


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---------- per-page, per-width checks ----------
    for lang, path in PAGES.items():
        for wname, w in WIDTHS.items():
            ctx = browser.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
            page = ctx.new_page()
            errors, failed = [], []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(300)
            # trigger reveal animations so full-page screenshots show content
            page.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-in'))")
            page.wait_for_timeout(700)

            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"[{lang} {wname}] no horizontal overflow", overflow <= 0, f"overflow={overflow}px")
            check(f"[{lang} {wname}] no console errors", not errors, "; ".join(errors)[:300] or "0 errors")
            check(f"[{lang} {wname}] no failed requests", not failed, "; ".join(failed)[:300] or "0 failed")

            if wname in ("360", "1440"):
                page.screenshot(path=str(SHOTS / f"{lang}-{wname}-full.png"), full_page=True)
            page.screenshot(path=str(SHOTS / f"{lang}-{wname}-top.png"))
            ctx.close()

    # ---------- direction and language ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    check("AR page: html lang=ar and dir=rtl",
          page.get_attribute("html", "lang") == "ar" and page.get_attribute("html", "dir") == "rtl")
    check("AR page: hero is first heading in Arabic",
          "عبدالعزيز" in page.inner_text("#hero-title"), page.inner_text("#hero-title"))
    check("AR page: hreflang alternates present",
          page.locator('link[rel="alternate"][hreflang="en"]').count() == 1)
    check("AR page: a single <h1>", page.locator("h1").count() == 1)

    # language switch: click, then verify the English page
    page.click("a.lang-switch")
    page.wait_for_load_state("networkidle")
    check("Language switch AR→EN navigates to /en/", page.url.rstrip("/").endswith("/en"), page.url)
    check("EN page: html lang=en and dir=ltr",
          page.get_attribute("html", "lang") == "en" and page.get_attribute("html", "dir") == "ltr")
    check("EN page: hero heading is English", "Abdulaziz" in page.inner_text("#hero-title"))
    page.click("a.lang-switch")
    page.wait_for_load_state("networkidle")
    check("Language switch EN→AR returns to /", page.url.rstrip("/").endswith(".com") or page.url.rstrip("/").endswith(":8000") or page.url.rstrip("/").endswith("/") and "/en" not in page.url, page.url)
    check("Language switch back: dir=rtl", page.get_attribute("html", "dir") == "rtl")
    ctx.close()

    # ---------- anchors, links, assets ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    for lang, path in PAGES.items():
        page.goto(BASE + path, wait_until="networkidle")
        hrefs = page.eval_on_selector_all("a[href^='#']", "els => els.map(e => e.getAttribute('href'))")
        missing = [h for h in set(hrefs) if h != "#" and page.locator(h).count() == 0]
        check(f"[{lang}] every in-page anchor has a target", not missing, f"missing={missing}")

        ext = page.eval_on_selector_all("a[href^='http']", "els => els.map(e => e.href)")
        check(f"[{lang}] no external links", not ext, f"found={ext}")

        imgs = page.eval_on_selector_all("img", "els => els.map(e => ({src:e.getAttribute('src'), ok: e.complete && e.naturalWidth>0, alt: e.getAttribute('alt')}))")
        check(f"[{lang}] every image loads and has alt text",
              all(i["ok"] and i["alt"] for i in imgs), json.dumps(imgs, ensure_ascii=False)[:200])

        fonts = page.evaluate("""() => Array.from(document.fonts).map(f => ({family: f.family, weight: f.weight, status: f.status}))""")
        loaded_or_unused = all(f["status"] in ("loaded", "unloaded") for f in fonts)
        check(f"[{lang}] fonts registered and not in error", loaded_or_unused and len(fonts) > 0, f"{len(fonts)} faces")

        dl = page.get_attribute("a[download]", "href")
        code, ctype = http_status(BASE + dl)
        check(f"[{lang}] CV download link resolves (200 + PDF)", code == 200 and "pdf" in ctype.lower(), f"{dl} -> {code} {ctype}")

        ld = page.inner_text("script[type='application/ld+json']") if False else page.evaluate(
            "() => JSON.parse(document.querySelector('script[type=\"application/ld+json\"]').textContent)")
        check(f"[{lang}] JSON-LD Person parses and has name", ld.get("@type") == "Person" and ld.get("name"), ld.get("name"))

        title = page.title()
        desc = page.get_attribute("meta[name=description]", "content")
        check(f"[{lang}] unique title (<=70 chars) and description (<=160)", title and len(title) <= 70 and desc and len(desc) <= 160,
              f"title={len(title)} desc={len(desc or '')}")

    # 404 page
    # The local python server returns a bare 404 for unknown paths; Vercel (cleanUrls) serves 404.html.
    r = page.goto(BASE + "/this-page-does-not-exist", wait_until="networkidle")
    check("Unknown path returns HTTP 404", r.status == 404, f"status={r.status}")
    r2 = page.goto(BASE + "/404.html", wait_until="networkidle")
    check("404.html page content is correct (bilingual message, noindex)",
          r2.status == 200 and "غير موجودة" in page.content() and "The page you requested" in page.content()
          and 'content="noindex"' in page.content(), f"status={r2.status}")
    ctx.close()

    # ---------- reduced motion: content must stay visible ----------
    ctx = browser.new_context(viewport={"width": 1024, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(300)
    hidden = page.evaluate("Array.from(document.querySelectorAll('.reveal')).filter(e => getComputedStyle(e).opacity === '0').length")
    check("Reduced motion: no reveal element left hidden", hidden == 0, f"hidden={hidden}")
    ctx.close()

    # ---------- no-JS: content must still be complete ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    visible_sections = page.evaluate("Array.from(document.querySelectorAll('section')).length")
    check("No-JS: all sections present in HTML", visible_sections == 9, f"sections={visible_sections}")
    ctx.close()

    # ---------- axe-core accessibility (WCAG 2.x A/AA) ----------
    for lang, path in PAGES.items():
        for wname in ("360", "1440"):
            ctx = browser.new_context(viewport={"width": WIDTHS[wname], "height": 900})
            page = ctx.new_page()
            page.goto(BASE + path, wait_until="networkidle")
            page.add_script_tag(path=str(AXE_JS))
            res = page.evaluate("""async () => {
                const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});
                return {violations: r.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help, sample: (v.nodes[0]||{}).html || '' })), passes: r.passes.length};
            }""")
            v = res["violations"]
            check(f"axe [{lang} {wname}] zero violations (WCAG 2.2 AA + best practice)", not v,
                  f"{len(v)} violations; passes={res['passes']}" + ("; " + json.dumps(v, ensure_ascii=False)[:400] if v else ""))
            ctx.close()

    browser.close()

out = ROOT / "docs" / "test-results.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n{len(report['checks']) - report['failures']}/{len(report['checks'])} passed")
sys.exit(1 if report["failures"] else 0)
