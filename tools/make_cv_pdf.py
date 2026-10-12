#!/usr/bin/env python3
"""Rebuild the downloadable CV (assets/docs/*.pdf) as a real, searchable A4 document.

The CV file used to be a scan-like PDF made of two page images: it had no text
layer, no embedded fonts and a non-A4 page size, so it could not be searched,
copied, translated or read by a screen reader. This script prints the built
Arabic page with the site's print stylesheet and saves the result, so the
download has selectable text and A4 pages.

Requirements (optional tooling, same as tests/run_checks.py):
    pip install playwright && python3 -m playwright install chromium

Usage:
    python3 tools/build.py && python3 tools/make_cv_pdf.py

Notes:
  * Run it after content changes so the file matches the site.
  * Replace the output with the original signed CV whenever one is available;
    see docs/UPDATE-CHECKLIST.md.
"""
import pathlib
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from threading import Thread
from functools import partial

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "docs" / "abdulaziz-al-qaeed-cv.pdf"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is required for this optional tool: pip install playwright")

    with tempfile.TemporaryDirectory() as tmp:
        site = pathlib.Path(tmp) / "dist"
        site.mkdir()
        (site / "index.html").write_text((ROOT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
        (site / "assets").symlink_to(ROOT / "assets")

        ThreadingTCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
        Thread(target=server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:%d/index.html" % server.server_address[1]

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1240, "height": 1754})
            page.goto(url, wait_until="networkidle")
            page.emulate_media(media="print")
            hidden = page.evaluate(
                "Array.from(document.querySelectorAll('.reveal'))"
                ".filter(e => parseFloat(getComputedStyle(e).opacity) < 0.9).length"
            )
            if hidden:
                raise SystemExit(f"Refusing to write a CV with {hidden} hidden blocks")
            page.pdf(path=str(OUTPUT), print_background=True, prefer_css_page_size=True)
            browser.close()
        server.shutdown()

    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size // 1024} KB, A4, selectable text)")


if __name__ == "__main__":
    sys.exit(main())
