#!/usr/bin/env python3
"""
End-to-end checks for the static site. Run while the site is being served:

  python3 tools/build.py && python3 tools/package.py
  python3 -m http.server 8000 --bind 0.0.0.0 --directory dist
  python3 tests/run_checks.py http://127.0.0.1:8000

Writes screenshots to docs/screenshots/ and a JSON report to docs/test-results.json.
Every result printed here is measured in the browser; nothing is assumed.
"""
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright
import axe_core_python

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
AXE_JS = pathlib.Path(axe_core_python.__file__).parent / "axe.min.js"

WIDTHS = {
    "360": 360, "375": 375, "430": 430, "768": 768, "861": 861, "900": 900,
    "1024": 1024, "1100": 1100, "1366": 1366, "1440": 1440, "1920": 1920,
}
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

            clipped_text = page.evaluate("""() => {
                const selectors = 'h1,h2,h3,p,.btn,.card,.focus-card,.pub,.tl-item,.cert-list li';
                return Array.from(document.querySelectorAll(selectors))
                    .filter(el => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && el.scrollWidth > el.clientWidth + 2;
                    })
                    .map(el => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${String(el.className || '').replace(/\s+/g, '.')}`)
                    .slice(0, 8);
            }""")
            check(f"[{lang} {wname}] no clipped text in key content", not clipped_text,
                  ", ".join(clipped_text) or "0 clipped elements")

            if w <= 768:
                nav_overflow = page.locator(".primary-nav").evaluate("el => el.scrollWidth - el.clientWidth")
                check(f"[{lang} {wname}] mobile navigation fits without horizontal scrolling",
                      nav_overflow <= 2, f"nav overflow={nav_overflow}px")

            text_overlaps = page.evaluate("""() => {
                const nodes = Array.from(document.querySelectorAll('h1,h2,h3,p'))
                    .filter(el => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0;
                    });
                const overlaps = [];
                for (let i = 0; i < nodes.length; i++) {
                    const a = nodes[i].getBoundingClientRect();
                    for (let j = i + 1; j < nodes.length; j++) {
                        const b = nodes[j].getBoundingClientRect();
                        const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
                        const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                        if (width > 1 && height > 1) {
                            overlaps.push(`${nodes[i].tagName.toLowerCase()} / ${nodes[j].tagName.toLowerCase()}`);
                        }
                    }
                }
                return overlaps.slice(0, 8);
            }""")
            check(f"[{lang} {wname}] no overlapping heading/paragraph boxes", not text_overlaps,
                  ", ".join(text_overlaps) or "0 overlaps")
            check(f"[{lang} {wname}] no console errors", not errors, "; ".join(errors)[:300] or "0 errors")
            check(f"[{lang} {wname}] no failed requests", not failed, "; ".join(failed)[:300] or "0 failed")

            if wname in ("375", "1366"):
                page.screenshot(path=str(SHOTS / f"{lang}-{wname}-full.png"), full_page=True)
            page.screenshot(path=str(SHOTS / f"{lang}-{wname}-top.png"))
            ctx.close()

    # ---------- direction and language ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    page.keyboard.press("Tab")
    focus_state = page.evaluate("""() => {
        const el = document.activeElement;
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
            visible: style.visibility !== 'hidden' && style.display !== 'none' && rect.bottom > 0,
            focusVisible: el.matches(':focus-visible'),
            outline: parseFloat(style.outlineWidth) > 0 && style.outlineStyle !== 'none',
        };
    }""")
    check("AR page: keyboard focus is visible on first Tab",
          focus_state["visible"] and focus_state["focusVisible"] and focus_state["outline"], str(focus_state))
    check("AR page: html lang=ar and dir=rtl",
          page.get_attribute("html", "lang") == "ar" and page.get_attribute("html", "dir") == "rtl")
    ar_copy = page.locator("body").inner_text()
    check("AR page: third-person biography of the Sheikh",
          page.inner_text("#about-title") == "نبذة عن الشيخ"
          and "الشيخ عبدالعزيز القعيد" in page.inner_text("#about")
          and not any(phrase in ar_copy for phrase in ("نبذة عني", "تواصل معي", "راسلني بالبريد", "إعدادي وكتابتي")))
    check("AR page: hero is first heading in Arabic",
          "عبدالعزيز" in page.inner_text("#hero-title"), page.inner_text("#hero-title"))
    check("AR page: hreflang alternates present",
          page.locator('link[rel="alternate"][hreflang="en"]').count() == 1)
    check("AR page: a single <h1>", page.locator("h1").count() == 1)
    check("AR page: contact section is inside the main landmark", page.locator("main #contact").count() == 1)

    # language switch: click, then verify the English page
    page.click("a.lang-switch")
    page.wait_for_load_state("networkidle")
    check("Language switch AR→EN navigates to /en/", page.url.rstrip("/").endswith("/en"), page.url)
    check("EN page: html lang=en and dir=ltr",
          page.get_attribute("html", "lang") == "en" and page.get_attribute("html", "dir") == "ltr")
    en_copy = page.locator("body").inner_text().lower()
    check("EN page: third-person biography of the Sheikh",
          page.inner_text("#about-title") == "Biography"
          and "Sheikh Abdulaziz Al-Qaeed" in page.inner_text("#about")
          and not any(phrase in en_copy for phrase in ("about me", "contact me", "email me", "my writing")))
    check("EN page: hero heading is English", "Abdulaziz" in page.inner_text("#hero-title"))
    check("EN page: contact section is inside the main landmark", page.locator("main #contact").count() == 1)
    page.keyboard.press("Tab")
    focus_state = page.evaluate("""() => {
        const el = document.activeElement;
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
            visible: style.visibility !== 'hidden' && style.display !== 'none' && rect.bottom > 0,
            focusVisible: el.matches(':focus-visible'),
            outline: parseFloat(style.outlineWidth) > 0 && style.outlineStyle !== 'none',
        };
    }""")
    check("EN page: keyboard focus is visible on first Tab",
          focus_state["visible"] and focus_state["focusVisible"] and focus_state["outline"], str(focus_state))
    page.click("a.lang-switch")
    page.wait_for_load_state("networkidle")
    # Port-agnostic: only the path matters, so the check also passes behind
    # Cloudflare Pages previews and any local port.
    check("Language switch EN→AR returns to /",
          urllib.parse.urlparse(page.url).path in ("", "/"), page.url)
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

        # Sticky headers must not cover the section reached by in-page navigation.
        # At 375px the horizontal nav is replaced by the section index, so the
        # check drives the index panel exactly like a phone user would.
        page.set_viewport_size({"width": 375, "height": 800})
        page.click(".toc-toggle")
        page.wait_for_timeout(200)
        page.locator('.toc-list a[href="#experience"]').first.click()
        page.wait_for_timeout(900)
        anchor_geometry = page.evaluate("""() => ({
            targetTop: document.querySelector('#experience').getBoundingClientRect().top,
            headerBottom: document.querySelector('.site-header').getBoundingClientRect().bottom,
        })""")
        check(f"[{lang}] sticky header does not cover anchor target at 375px",
              anchor_geometry["targetTop"] >= anchor_geometry["headerBottom"] - 1,
              str(anchor_geometry))
        page.set_viewport_size({"width": 1440, "height": 900})

        ext = page.eval_on_selector_all("a[href^='http']", "els => els.map(e => e.href)")
        check(f"[{lang}] no external links", not ext, f"found={ext}")

        imgs = page.eval_on_selector_all("img", """els => els.map(e => ({
            src: e.getAttribute('src'),
            ok: e.complete && e.naturalWidth > 0,
            alt: e.getAttribute('alt'),
            decorativeContext: e.closest('[aria-hidden="true"]') !== null,
        }))""")
        check(f"[{lang}] every image loads, and has either alt text or a decorative context",
              all(i["ok"] and (i["alt"] or i["decorativeContext"]) for i in imgs),
              json.dumps(imgs, ensure_ascii=False)[:200])

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
    # A plain local static server returns its own 404; check the 404 document directly.
    r = page.goto(BASE + "/this-page-does-not-exist", wait_until="networkidle")
    check("Unknown path returns HTTP 404", r.status == 404, f"status={r.status}")
    r2 = page.goto(BASE + "/404.html", wait_until="networkidle")
    check("404.html page content is correct (bilingual message, noindex)",
          r2.status == 200 and "غير موجودة" in page.content() and "The page you requested" in page.content()
          and 'content="noindex"' in page.content(), f"status={r2.status}")
    ctx.close()

    # ---------- reduced motion: content must stay visible ----------
    ctx = browser.new_context(viewport={"width": 375, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(300)
    hidden = page.evaluate("Array.from(document.querySelectorAll('.reveal')).filter(e => getComputedStyle(e).opacity === '0').length")
    check("Reduced motion: no reveal element left hidden", hidden == 0, f"hidden={hidden}")
    page.locator(".btn-primary").hover()
    motion = page.evaluate("""() => ({
        scroll: getComputedStyle(document.documentElement).scrollBehavior,
        transition: getComputedStyle(document.querySelector('.btn-primary')).transitionDuration,
        transform: getComputedStyle(document.querySelector('.btn-primary')).transform,
    })""")
    check("Reduced motion: scroll and button motion disabled",
          motion["scroll"] == "auto" and all(x.strip() in ("0s", "0ms") for x in motion["transition"].split(","))
          and motion["transform"] == "none", str(motion))
    ctx.close()

    # ---------- no-JS: content must still be complete ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    visible_sections = page.evaluate("Array.from(document.querySelectorAll('section')).length")
    check("No-JS: all sections present in HTML", visible_sections == 9, f"sections={visible_sections}")
    ctx.close()

    # ---------- print output (the site doubles as a printable CV) ----------
    for lang, path in PAGES.items():
        ctx = browser.new_context(viewport={"width": 1240, "height": 1754})
        page = ctx.new_page()
        page.goto(BASE + path, wait_until="networkidle")
        page.emulate_media(media="print")
        page.wait_for_timeout(300)
        print_state = page.evaluate("""() => ({
            hiddenReveals: Array.from(document.querySelectorAll('.reveal'))
                .filter(e => parseFloat(getComputedStyle(e).opacity) < 0.9).length,
            printHeader: getComputedStyle(document.querySelector('.print-head')).display !== 'none',
            screenOnlyHidden: ['header', '.to-top-wrap'].every(sel => getComputedStyle(document.querySelector(sel)).display === 'none'),
            bodyText: document.body.innerText.length,
        })""")
        check(f"[{lang}] print: no content block is left invisible",
              print_state["hiddenReveals"] == 0, f"hidden={print_state['hiddenReveals']}")
        check(f"[{lang}] print: document header shown, interactive chrome hidden",
              print_state["printHeader"] and print_state["screenOnlyHidden"], str(print_state))
        check(f"[{lang}] print: the document carries the full text",
              print_state["bodyText"] > 3000, f"{print_state['bodyText']} chars")
        page.emulate_media(media="screen")
        ctx.close()

    # ---------- header integrity across the widths that used to clip ----------
    for lang, path in PAGES.items():
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        page.goto(BASE + path, wait_until="networkidle")
        clipped = {}
        header_heights = {}
        for width in (768, 861, 900, 1024, 1100, 1180, 1366, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(120)
            state = page.evaluate("""() => ({
                header: Math.round(document.querySelector('.site-header').getBoundingClientRect().height),
                clipped: Array.from(document.querySelectorAll('.primary-nav a, .lang-switch, .toc-toggle, .brand-name'))
                    .filter(el => { const r = el.getBoundingClientRect();
                        return r.width > 0 && (r.left < -1 || r.right > innerWidth + 1); })
                    .map(el => el.textContent.trim()),
            })""")
            if state["clipped"]:
                clipped[width] = state["clipped"]
            header_heights[width] = state["header"]
        check(f"[{lang}] no header or navigation item is clipped (768-1920px)", not clipped, json.dumps(clipped, ensure_ascii=False)[:200])
        check(f"[{lang}] header stays a single compact row from 768px up",
              max(header_heights.values()) <= 80, json.dumps(header_heights))
        ctx.close()

    # ---------- header height must not depend on which fonts arrived ----------
    for lang, path in PAGES.items():
        for _ in range(2):
            ctx = browser.new_context(viewport={"width": 375, "height": 812})
            page = ctx.new_page()
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(400)
            height = page.evaluate("Math.round(document.querySelector('.site-header').getBoundingClientRect().height)")
            report.setdefault("header_mobile", {}).setdefault(lang, []).append(height)
            ctx.close()
        heights = report["header_mobile"][lang]
        check(f"[{lang}] mobile header is compact and stable across loads (<=64px, spread <= 2px)",
              max(heights) <= 64 and max(heights) - min(heights) <= 2, f"heights={heights}")

    # ---------- the section index panel ----------
    for lang, path in PAGES.items():
        for width in (375, 768, 1366):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            page = ctx.new_page()
            page.goto(BASE + path, wait_until="networkidle")
            page.click(".toc-toggle")
            page.wait_for_timeout(200)
            panel = page.evaluate("""() => {
                const panel = document.querySelector('.toc-panel');
                const box = panel.getBoundingClientRect();
                const header = document.querySelector('.site-header').getBoundingClientRect();
                const offenders = Array.from(panel.querySelectorAll('a, summary'))
                    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && (r.left < -1 || r.right > innerWidth + 1); }).length;
                return {left: box.left, right: box.right, top: box.top, headerBottom: header.bottom,
                        width: innerWidth, offenders, links: panel.querySelectorAll('.toc-list a').length};
            }""")
            check(f"[{lang} {width}] section index opens inside the viewport with all {len(page.query_selector_all('.toc-list a'))} sections",
                  panel["offenders"] == 0 and panel["left"] >= -1 and panel["right"] <= panel["width"] + 1
                  and panel["top"] >= panel["headerBottom"] - 2 and panel["links"] == 8,
                  json.dumps(panel))
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            check(f"[{lang} {width}] Escape closes the section index",
                  not page.evaluate("() => document.querySelector('[data-toc]').open"))
            ctx.close()

    # ---------- in-page state: current section, back-to-top, print action ----------
    for lang, path in PAGES.items():
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        page.goto(BASE + path, wait_until="networkidle")
        top_state = page.evaluate("() => document.querySelector('[data-back-to-top]').hidden")
        check(f"[{lang}] back-to-top stays hidden at the top of the page", top_state)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
        page.wait_for_timeout(500)
        state = page.evaluate("""() => ({
            backToTop: !document.querySelector('[data-back-to-top]').hidden,
            current: document.querySelectorAll('.primary-nav a[aria-current="location"], .toc-list a[aria-current="location"]').length,
            printEnabled: !document.querySelector('[data-print]').hidden,
        })""")
        check(f"[{lang}] the current section is marked once for keyboard and screen readers",
              state["current"] >= 1 and state["current"] <= 3, f"aria-current elements={state['current']}")
        check(f"[{lang}] back-to-top and the print action appear while reading",
              state["backToTop"] and state["printEnabled"], str(state))
        ctx.close()

    # ---------- the language switch keeps the reader in the same section ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(BASE + "/#community", wait_until="networkidle")
    href = page.get_attribute(".lang-switch", "href")
    check("Language switch keeps the current section", href.endswith("/en/#community"), href)
    page.click(".lang-switch")
    page.wait_for_load_state("networkidle")
    check("Language switch lands on the same section (EN)",
          page.url.rstrip("/").endswith("/en/#community"), page.url)
    ctx.close()

    # ---------- touch targets ----------
    for lang, path in PAGES.items():
        for width in (375, 1366):
            ctx = browser.new_context(viewport={"width": width, "height": 812})
            page = ctx.new_page()
            page.goto(BASE + path, wait_until="networkidle")
            targets = page.evaluate("""() => Array.from(document.querySelectorAll('a, button, summary'))
                .filter(el => el.getBoundingClientRect().width > 0)
                .map(el => ({t: (el.innerText || '').trim().slice(0, 24),
                             h: Math.round(el.getBoundingClientRect().height)}))""")
            small = [t for t in targets if t["h"] < 24]
            comfortable = [t for t in targets if t["h"] < 44]
            check(f"[{lang} {width}] no touch target below 24px (WCAG 2.5.8)",
                  not small, json.dumps(small, ensure_ascii=False)[:200])
            check(f"[{lang} {width}] every target reaches the 44px comfort size",
                  not comfortable, f"{len(comfortable)} of {len(targets)} below 44px")
            ctx.close()

    # ---------- the downloadable CV is a real text document ----------
    try:
        from pypdf import PdfReader
        import io as _io
        with urllib.request.urlopen(BASE + "/assets/docs/abdulaziz-al-qaeed-cv.pdf", timeout=30) as response:
            data = response.read()
        reader = PdfReader(_io.BytesIO(data))
        page_size = reader.pages[0].mediabox
        text_chars = sum(len((p.extract_text() or "").strip()) for p in reader.pages)
        a4 = abs(float(page_size.width) - 595) < 2 and abs(float(page_size.height) - 842) < 2
        check("CV download is an A4 document with selectable text",
              a4 and text_chars > 2000,
              f"pages={len(reader.pages)} size={round(float(page_size.width))}x{round(float(page_size.height))}pt text={text_chars} chars {len(data)//1024}KB")
    except ImportError:
        print("SKIP CV text check (pip install pypdf)")

    # ---------- webfont subsets still cover every character on the pages ----------
    # The fonts in assets/fonts/ are subsets (tools/subset_fonts.py). If new
    # content introduces a character outside the recorded set, the browser would
    # fall back to a system font mid-sentence — fail loudly instead. The character
    # set is computed by the same helper the subsetting tool uses, so both sides
    # always agree on what "the characters on the pages" means.
    manifest = ROOT / "docs" / "font-subset.json"
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from subset_fonts import used_characters
        covered = set(json.loads(manifest.read_text(encoding="utf-8"))["used_characters"])
        current = used_characters()
        missing = sorted(current - covered)
        check("webfont subsets cover every character now on the pages",
              not missing,
              "re-run tools/subset_fonts.py -> missing " + "".join(missing)[:80] if missing
              else f"{len(current)} characters covered by {manifest.name}")
    except Exception as exc:  # missing manifest, unreadable file, import error
        check("webfont subsets cover every character now on the pages", False, f"{type(exc).__name__}: {exc}")

    # ---------- axe-core accessibility (WCAG 2.x A/AA) ----------
    for lang, path in PAGES.items():
        for wname in ("375", "1366"):
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
