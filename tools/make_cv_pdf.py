#!/usr/bin/env python3
"""Generate a review-only, searchable A4 PDF from the current Arabic page.

  python3 tools/build.py
  python3 tools/make_cv_pdf.py --output test-results/cv-preview.pdf

Requires Playwright/Chromium. Output is required to prevent overwriting an
owner-approved or signed downloadable CV by accident. Publishing a replacement
at assets/docs/abdulaziz-al-qaeed-cv.pdf requires explicit owner approval.
"""
import pathlib
import argparse
import os
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from threading import Thread
from functools import partial

ROOT = pathlib.Path(__file__).resolve().parent.parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Refusing to overwrite an existing PDF; choose a new review output")
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

        output.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            options = {"executable_path": os.environ["CHROMIUM_EXECUTABLE_PATH"]} if os.environ.get("CHROMIUM_EXECUTABLE_PATH") else {}
            browser = p.chromium.launch(**options)
            page = browser.new_page(viewport={"width": 1240, "height": 1754})
            page.goto(url, wait_until="networkidle")
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready")
            if not page.locator("#about").is_visible() or not page.locator("#contact").is_visible():
                raise SystemExit("Refusing to write a PDF with hidden biography content")
            page.pdf(path=str(output), format="A4", print_background=True, prefer_css_page_size=True)
            browser.close()
        server.shutdown()

    print(f"wrote {output} ({output.stat().st_size // 1024} KB, A4, selectable text)")


if __name__ == "__main__":
    sys.exit(main())
