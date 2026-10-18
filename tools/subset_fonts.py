#!/usr/bin/env python3
"""Compatibility entry point; legacy subsetting was retired after NDS adoption.

The old tool targeted styles.css and fonts no longer served by this site.
NDS fonts are vendor assets: verify coverage, never rewrite them in place.
"""
from check_fonts import main

if __name__ == '__main__':
    print('Legacy subsetting retired; running read-only NDS font coverage instead.')
    main()
