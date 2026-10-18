#!/usr/bin/env python3
"""Create annotated copies of audit screenshots (originals unchanged).

Draws numbered markers over evidence PNGs by rendering an HTML overlay in the
same local Chromium used for captures. Output: docs/visual-audit/evidence/annotated/

Usage: LD_LIBRARY_PATH=/tmp/al2023/lib CHROMIUM_EXECUTABLE_PATH=/tmp/chromium \
       .venv/bin/python docs/visual-audit/annotate.py
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "evidence"
OUT = EVID / "annotated"
OUT.mkdir(parents=True, exist_ok=True)
EXECUTABLE = os.environ.get("CHROMIUM_EXECUTABLE_PATH", None)

# (source, [(x_pct, y_pct, n), ...]) — marker positions as % of image size.
JOBS = {
    "home-ar-1440-top.png": [
        (14, 30, 1),   # hero left island / dead zone under buttons
        (64, 22, 2),   # h1 name block small relative to page
        (88, 25, 3),   # portrait 120px circular crop
        (72, 28, 4),   # title + tagline run-on
        (35, 52, 5),   # intro measure vs body measure
        (26, 63, 6),   # facts -> body gap tight
        (13, 4, 7),    # orphaned language icon far from nav
    ],
    "home-en-1440-top.png": [
        (40, 50, 1),   # EN intro measure
        (55, 82, 2),   # body paragraph ~115 chars/line
        (20, 22, 3),   # hero dead zone under CTA row
        (48, 22, 4),   # identical type scale AR/EN
    ],
    "home-ar-390-top.png": [
        (72, 4, 1),    # header title truncation
        (75, 52, 2),   # share button narrower than siblings
        (42, 28, 3),   # cramped text column beside avatar
        (80, 72, 4),   # TOC list wall pushes content below fold
    ],
    "home-en-390-top.png": [
        (38, 22, 1),   # "Al-" / "Qaed" hyphen break in h1
        (25, 58, 2),   # share button width mismatch
    ],
    "home-ar-1440-section-experience.png": [
        (71, 76, 1),   # hollow dot on oldest step (data-current=5)
        (12, 45, 2),   # large void left of timeline in AR
        (65, 40, 3),   # Hijri range mirrored visually
    ],
    "home-ar-1440-toc-active.png": [
        (38, 31, 1),   # publication card mostly empty
        (38, 45, 2),   # repeated card rhythm, single tag only
    ],
    "home-ar-1440-footer.png": [
        (55, 23, 1),   # email card: right half only, left void
        (13, 35, 2),   # lone documentation note
    ],
    "notfound-ar-1440-top.png": [
        (50, 30, 1),   # 404 numeral off-palette slate
        (45, 20, 2),   # scattered icon confetti diverges from identity
    ],
}

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#111}}
#wrap{{position:relative;width:1440px}}
#wrap img{{display:block;width:100%}}
.mk{{position:absolute;width:34px;height:34px;border-radius:50%;
background:#d93025;color:#fff;font:700 20px/34px system-ui,sans-serif;
text-align:center;box-shadow:0 0 0 3px #fff,0 2px 8px rgba(0,0,0,.45);
transform:translate(-50%,-50%);z-index:9}}
</style></head><body><div id="wrap"><img src="{src}">{markers}</div></body></html>"""


def main():
    with sync_playwright() as p:
        opts = {"executable_path": EXECUTABLE} if EXECUTABLE else {}
        browser = p.chromium.launch(**opts)
        for name, marks in JOBS.items():
            src = EVID / name
            if not src.is_file():
                print("skip missing", name)
                continue
            markers = "".join(
                f'<div class="mk" style="left:{x}%;top:{y}%">{n}</div>'
                for x, y, n in marks)
            html = TEMPLATE.format(src=src.resolve().as_uri(), markers=markers)
            tmp_html = OUT / f"_tmp-{src.stem}.html"
            tmp_html.write_text(html, encoding="utf-8")
            width = 1440  # viewport width; corrected to natural width below
            page = browser.new_page(viewport={"width": width, "height": 1000})
            page.goto(tmp_html.resolve().as_uri(), wait_until="load")
            page.wait_for_function("document.querySelector('#wrap img').complete")
            page.wait_for_timeout(300)
            width = page.evaluate("document.querySelector('#wrap img').naturalWidth")
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate(f"document.getElementById('wrap').style.width='{width}px'")
            page.wait_for_timeout(200)
            el = page.locator("#wrap")
            el.screenshot(path=str(OUT / name))
            print("annotated", name)
            page.close()
        for tmp in OUT.glob("_tmp-*.html"):
            tmp.unlink()
        browser.close()


if __name__ == "__main__":
    main()
