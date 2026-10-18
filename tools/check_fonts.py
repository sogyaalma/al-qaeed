#!/usr/bin/env python3
"""Read-only glyph coverage check for the actual NDS IBM Plex fonts.

Never subsets or overwrites vendor fonts. Requires fonttools and brotli from
requirements-test.txt. The former docs/font-subset.json is historical only.
"""
from html.parser import HTMLParser
from pathlib import Path
import unicodedata

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.characters = set()

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        for key, value in attrs:
            if key in ('alt', 'aria-label', 'title') and value:
                self.characters.update(value)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.characters.update(data)


def main():
    coverage = set()
    names = ['IBMPlexSansArabic-Regular.woff2', 'IBMPlexSans-Regular-Latin1.woff2']
    for name in names:
        with TTFont(ROOT / 'assets/fonts' / name) as font:
            coverage.update(font.getBestCmap())
    for name in ('index.html', 'en/index.html', '404.html'):
        parser = Text()
        parser.feed((ROOT / name).read_text(encoding='utf-8'))
        required = {ord(c) for c in parser.characters if not c.isspace() and unicodedata.category(c) != 'Cf'}
        missing = sorted(required - coverage)
        if missing:
            raise SystemExit(f'FAIL {name}: missing glyphs ' + ', '.join(f'U+{c:04X}' for c in missing))
        print(f'PASS {name}: {len(required)} text/accessible-label characters covered by actual IBM Plex fonts')


if __name__ == '__main__':
    main()
