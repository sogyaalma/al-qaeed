#!/usr/bin/env python3
"""Real Cloudflare preview routing, content, headers and publication checks.

Run on GitHub's runner; the Arena sandbox cannot reach pages.dev. No writes to
Cloudflare, production deployment, credentials, external services, or settings.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1].rstrip('/')
if not re.fullmatch(r'https://[0-9a-f]{8}\.al-qaeed\.pages\.dev', BASE):
    raise SystemExit('Only an immutable al-qaeed Cloudflare preview URL is allowed')
checks = []


def check(name, ok, detail=''):
    checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + detail if detail else ''), flush=True)


def get(path):
    try:
        return urlopen(BASE + path, timeout=30)
    except HTTPError as response:
        return response


def main():
    expected_headers = dict(line.strip().split(': ', 1) for line in (ROOT / 'dist/_headers').read_text().splitlines() if line.startswith('  '))
    for path, file, status in [('/', 'index.html', 200), ('/en/', 'en/index.html', 200),
                               ('/missing/audit/', '404.html', 404)]:
        with get(path) as response:
            data = response.read()
            check(path + ' HTTP status', response.status == status, str(response.status))
            check(path + ' correct generated HTML', data == (ROOT / 'dist' / file).read_bytes())
            for name, value in expected_headers.items():
                check(path + ' ' + name, response.headers.get(name) == value, str(response.headers.get(name)))
    for path, destination in [('/index.html', '/'), ('/en', '/en/'), ('/en/index.html', '/en/')]:
        with get(path) as response:
            check(path + ' canonical routing', response.status == 200 and response.geturl() == BASE + destination, response.geturl())
    for path in ['robots.txt', 'sitemap.xml', 'assets/docs/abdulaziz-al-qaeed-cv.pdf',
                 'assets/css/nds.critical.min.css', 'assets/css/nds-main.min.css',
                 'assets/css/hgi-rounded-stroke-min.css', 'assets/fonts/hgi-blank.woff2']:
        with get('/' + path) as response:
            check(path + ' published bytes', response.status == 200 and hashlib.sha256(response.read()).digest() == hashlib.sha256((ROOT / 'dist' / path).read_bytes()).digest())
    for name in json.loads((ROOT / 'docs/nds-assets.json').read_text())['distribution_excluded_fonts']:
        with get('/' + name) as response:
            check(name + ' not publicly distributed', response.status == 404, str(response.status))
    for path in ['/content/content.json', '/tools/build.py', '/.git/config']:
        with get(path) as response:
            check(path + ' repository internals not published', response.status == 404, str(response.status))


try:
    main()
except Exception as exc:
    check('provider suite completed', False, f'{type(exc).__name__}: {exc}')
finally:
    out = ROOT / 'test-results'
    out.mkdir(exist_ok=True)
    (out / 'cloudflare-preview.json').write_text(json.dumps({'base': BASE, 'checks': checks}, indent=2) + '\n')
    summary = f'{sum(c["ok"] for c in checks)}/{len(checks)} provider checks passed at {BASE}'
    print(summary)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print('::notice title=Cloudflare preview verification::' + summary)
sys.exit(0 if checks and all(c['ok'] for c in checks) else 1)
