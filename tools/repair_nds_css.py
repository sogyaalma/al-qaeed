#!/usr/bin/env python3
"""Reproducible encoding/asset-URL repair; no NDS component rule is rewritten.

Remove the misplaced BOM breaking :root, externalize the identical blank font
without widening CSP. Accept only inherited input, intermediate BOM repair or
final repaired bytes. This is not an NDS upgrade or a general minifier.
"""
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / 'assets/css/nds-main.min.css'
ORIGINAL_SHA256 = '46960f4f3d23b69808437d93832fb822c3ffa5684cb17d4298172241da7241d6'
ENCODING_ONLY_SHA256 = 'd68f2f47b362dbec410f24e75fc934855706b2d12793ddf7860b62e126587a55'
REPAIRED_SHA256 = '3a60a169f1d32ff313851849ad6d76dc641860f7d0e4b4a045cb00738f9d8670'


def main():
    data = PATH.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest == REPAIRED_SHA256:
        print('NDS CSS encoding and local font URL already repaired')
        return
    if digest not in (ORIGINAL_SHA256, ENCODING_ONLY_SHA256):
        raise SystemExit('Unexpected NDS CSS: review source before applying repair')
    font = (ROOT / 'assets/fonts/hgi-blank.woff2').read_bytes()
    embedded = b'data:font/woff2;base64,' + base64.b64encode(font)
    if data.count(embedded) != 1:
        raise SystemExit('Expected exactly one matching embedded blank font')
    repaired = data.replace(b'\xef\xbb\xbf', b'').replace(embedded, b'../fonts/hgi-blank.woff2')
    if hashlib.sha256(repaired).hexdigest() != REPAIRED_SHA256:
        raise SystemExit('Unexpected repaired output')
    PATH.write_bytes(repaired)
    print('Removed misplaced BOM and externalized identical font; CSP unchanged')


if __name__ == '__main__':
    main()
