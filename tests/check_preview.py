#!/usr/bin/env python3
"""Real Cloudflare HTTP checks through an actual Chromium browser connection.

Cloudflare rejects Python urllib's client (403) on this project while serving
real browsers. Use browser fetch, not a fabricated UA, a security exemption,
a changed provider setting, or a hidden failure. Keep the raw-client failure
in the audit history. Run on GitHub's runner; Arena cannot reach pages.dev.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1].rstrip('/')
if not re.fullmatch(r'https://[0-9a-f]{8}\.al-qaeed\.pages\.dev', BASE):
    raise SystemExit('Only an immutable al-qaeed Cloudflare preview URL is allowed')
checks = []


def check(name, ok, detail=''):
    checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + detail if detail else ''), flush=True)
    if not ok and os.environ.get('GITHUB_ACTIONS') == 'true':
        message = (name + ': ' + detail).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=Provider verification::' + message, flush=True)


def main(page):
    # fetch uses this real browser's network stack, cookies, UA and same-origin
    # CSP. Redirects and binary downloads are inspected without executing HTML.
    def get(path):
        result = page.evaluate('''async path => {
            const r = await fetch(path, {cache:'no-store', redirect:'follow'});
            return {status:r.status, url:r.url, headers:Object.fromEntries(r.headers),
                    body:Array.from(new Uint8Array(await r.arrayBuffer()))};
        }''', path)
        result['body'] = bytes(result['body'])
        return result

    expected_headers = dict(line.strip().split(': ', 1) for line in (ROOT / 'dist/_headers').read_text().splitlines() if line.startswith('  '))
    for path, file, status in [('/', 'index.html', 200), ('/en/', 'en/index.html', 200),
                               ('/missing/audit/', '404.html', 404)]:
        response = get(path)
        check(path + ' HTTP status', response['status'] == status, str(response['status']))
        check(path + ' correct generated HTML', response['body'] == (ROOT / 'dist' / file).read_bytes())
        for name, value in expected_headers.items():
            actual = response['headers'].get(name.lower())
            check(path + ' ' + name, actual == value, str(actual))
    for path, destination in [('/index.html', '/'), ('/en', '/en/'), ('/en/index.html', '/en/')]:
        response = get(path)
        check(path + ' canonical routing', response['status'] == 200 and response['url'] == BASE + destination, response['url'])
    for path in ['robots.txt', 'sitemap.xml', 'assets/docs/abdulaziz-al-qaeed-cv.pdf',
                 'assets/css/nds.critical.min.css', 'assets/css/nds-main.min.css',
                 'assets/css/hgi-rounded-stroke-min.css', 'assets/fonts/hgi-blank.woff2']:
        response = get('/' + path)
        check(path + ' published bytes', response['status'] == 200 and hashlib.sha256(response['body']).digest() == hashlib.sha256((ROOT / 'dist' / path).read_bytes()).digest())
    for name in json.loads((ROOT / 'docs/nds-assets.json').read_text())['distribution_excluded_fonts']:
        response = get('/' + name)
        check(name + ' not publicly distributed', response['status'] == 404, str(response['status']))
    for path in ['/content/content.json', '/tools/build.py', '/.git/config']:
        response = get(path)
        check(path + ' repository internals not published', response['status'] == 404, str(response['status']))


try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        response = page.goto(BASE + '/', wait_until='networkidle')
        check('real browser initial document served', response.status == 200, str(response.status))
        main(page)
        browser.close()
except Exception as exc:
    check('provider suite completed', False, f'{type(exc).__name__}: {exc}')
finally:
    out = ROOT / 'test-results'
    out.mkdir(exist_ok=True)
    (out / 'cloudflare-preview.json').write_text(json.dumps({'base': BASE, 'transport': 'real Chromium browser fetch', 'checks': checks}, indent=2) + '\n')
    summary = f'{sum(c["ok"] for c in checks)}/{len(checks)} provider checks passed at {BASE}'
    print(summary)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print('::notice title=Cloudflare preview verification::' + summary)
sys.exit(0 if checks and all(c['ok'] for c in checks) else 1)
