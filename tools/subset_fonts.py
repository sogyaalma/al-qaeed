#!/usr/bin/env python3
"""
Rebuild the webfont subsets from the characters the site actually uses.

Why: the shipped IBM Plex Sans Arabic / Noto Naskh / Satoshi files are the full
Google Fonts slices (Arabic block + presentation forms, Latin ext, …). The site
uses ~130 unique characters, so most of those glyphs are dead weight on a slow
connection. This tool rewrites each file in place as a woff2 subset that still
covers the whole standard Arabic letter set (so ordinary new text keeps working)
plus every character present in the built pages.

Requirements (tooling only, not needed to deploy):
    pip install fonttools brotli

Run after tools/build.py, before tools/make_cv_pdf.py and tools/package.py:

    python3 tools/build.py
    python3 tools/subset_fonts.py
    python3 tools/make_cv_pdf.py
    python3 tools/package.py

The original full files are kept in tools/fonts-original/ (never deployed) so the
subsets can be regenerated at any time; docs/font-subset.json records exactly
which characters the current files cover, and tests/run_checks.py fails if a
page ever uses a character outside that record.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
ORIGINALS = ROOT / "tools" / "fonts-original"
MANIFEST = ROOT / "docs" / "font-subset.json"

# Safety margin: characters kept even if the current pages do not use them, so
# that editing content.json alone cannot produce tofu.
ARABIC_SET = [
    "U+060C", "U+061B", "U+061F",           # ، ؛ ؟
    "U+0621-064A",                          # standard Arabic letters
    "U+0640", "U+064B-0652", "U+0653-0655", "U+0670",   # tatweel + diacritics
    "U+0660-0669", "U+066A-066D",           # Arabic-Indic digits and marks
    "U+0671-06D3", "U+06D5", "U+06F0-06F9",  # extended Arabic letters/digits
    "U+200C-200F",                          # ZWNJ/ZWJ/LRM/RLM
]
LATIN_SET = [
    "U+0020-007E", "U+00A0", "U+00A9", "U+00AB", "U+00B7", "U+00BB",
    "U+2013-2014", "U+2018-201D", "U+2026", "U+2190-2193",
]
FONT_FILES = [
    ("ibm-plex-sans-arabic-arabic-400-normal.woff2", ARABIC_SET),
    ("ibm-plex-sans-arabic-arabic-600-normal.woff2", ARABIC_SET),
    ("ibm-plex-sans-arabic-arabic-700-normal.woff2", ARABIC_SET),
    ("ibm-plex-sans-arabic-latin-400-normal.woff2", LATIN_SET),
    ("ibm-plex-sans-arabic-latin-600-normal.woff2", LATIN_SET),
    ("ibm-plex-sans-arabic-latin-700-normal.woff2", LATIN_SET),
    ("noto-naskh-arabic-arabic-400-normal.woff2", ARABIC_SET),
    ("satoshi-500.woff2", LATIN_SET),
    ("satoshi-700.woff2", LATIN_SET),
]


def used_characters():
    """Every character the built site can render, from the HTML, the source
    JSON and the stylesheet (which may carry Arabic text in content rules)."""
    chars = set()
    for name in ("index.html", "en/index.html", "404.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S)
        chars |= set(re.sub(r"<[^>]+>", " ", text))
    chars |= set((ROOT / "content" / "content.json").read_text(encoding="utf-8"))
    chars |= set((ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8"))
    return {c for c in chars if c.isprintable() and c not in "{}<>[]\"\\"}


def unicodes_for(base, chars):
    points = set()
    for item in base:
        if item.startswith("U+"):
            body = item[2:]
            if "-" in body:
                lo, hi = (int(part, 16) for part in body.split("-"))
                points.update(range(lo, hi + 1))
            else:
                points.add(int(body, 16))
    points.update(ord(c) for c in chars if c.strip())
    return ",".join(f"U+{p:04X}" for p in sorted(points))


def main():
    try:
        import brotli  # noqa: F401
        from fontTools.subset import main as pyftsubset  # noqa: F401
    except ImportError:
        raise SystemExit(
            "fonttools and brotli are required for this tooling step:\n"
            "    pip install fonttools brotli"
        )

    chars = used_characters()
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    FONTS.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_by": "tools/subset_fonts.py",
        "used_characters": "".join(sorted(chars)),
        "used_character_count": len(chars),
        "files": [],
    }

    for name, base in FONT_FILES:
        source = FONTS / name
        if not source.exists():
            raise SystemExit(f"missing font file: {source}")
        # keep one untouched copy of the original slice
        original = ORIGINALS / name
        if not original.exists():
            shutil.copy2(source, original)
        before = source.stat().st_size

        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / name
            subprocess.run(
                [
                    sys.executable, "-m", "fontTools.subset", str(original),
                    f"--unicodes={unicodes_for(base, chars)}",
                    "--layout-features=*",     # keep Arabic shaping (init/medi/fina/liga/mark)
                    "--flavor=woff2",
                    f"--output-file={out}",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            data = out.read_bytes()
        source.write_bytes(data)
        report["files"].append({
            "file": name,
            "original_bytes": before,
            "subset_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()[:16],
        })
        print(f"{name:48s} {before/1024:6.1f} -> {len(data)/1024:6.1f} KB")

    total_before = sum(f["original_bytes"] for f in report["files"])
    total_after = sum(f["subset_bytes"] for f in report["files"])
    report["total_original_bytes"] = total_before
    report["total_subset_bytes"] = total_after
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\ntotal {total_before/1024:.1f} -> {total_after/1024:.1f} KB "
          f"(-{100 - total_after * 100 / total_before:.0f}%) | manifest: docs/font-subset.json")


if __name__ == "__main__":
    main()
