#!/usr/bin/env python3
"""Check local Markdown links in current operational docs (not historical reports)."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CURRENT = [
    'README.md', 'DEPLOY.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'docs/NDS-INTEGRATION.md', 'docs/DESIGN-TOKENS.md',
    'docs/UPDATE-CHECKLIST.md', 'docs/AUDIT-2026-10-18.md',
]
failed = []
count = 0
for name in CURRENT:
    path = ROOT / name
    if not path.is_file():
        failed.append(name + ': missing document')
        continue
    for href in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        url = urlsplit(href)
        if url.scheme or url.netloc or not url.path:
            continue
        count += 1
        if not (path.parent / unquote(url.path)).exists():
            failed.append(f'{name}: {href}')
for failure in failed:
    print('FAIL ' + failure)
print(f'{count} local links in {len(CURRENT)} current docs checked; {len(failed)} broken. Historical reports explicitly excluded.')
sys.exit(bool(failed))
