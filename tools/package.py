#!/usr/bin/env python3
"""Package only public static-site files for Cloudflare Pages.

Run after tools/build.py:
  python3 tools/build.py && python3 tools/package.py

The generated dist/ directory deliberately excludes repository documentation,
tests, source content and build tooling.
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist"
PUBLIC_FILES = ("index.html", "404.html", "robots.txt", "sitemap.xml", "_headers")


def main():
    # Validate inputs before replacing a previous package.
    for relative in PUBLIC_FILES:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Required public file is missing: {relative}")
    english = ROOT / "en" / "index.html"
    if not english.is_file():
        raise SystemExit("Required public file is missing: en/index.html")
    assets = ROOT / "assets"
    if not assets.is_dir():
        raise SystemExit("Required public directory is missing: assets/")

    # Reject links before touching an existing output: copytree follows them by
    # default and could accidentally publish private files outside the repository.
    inputs = [ROOT / name for name in PUBLIC_FILES] + [ROOT / "en", english, assets]
    inputs.extend(assets.rglob("*"))
    for source in inputs:
        if source.is_symlink():
            raise SystemExit(f"Refusing to package symlink: {source.relative_to(ROOT)}")

    # Do not follow or delete a symlink if dist/ has been replaced unexpectedly.
    if OUTPUT.is_symlink():
        raise SystemExit("Refusing to package: dist/ is a symlink")
    if OUTPUT.exists():
        if OUTPUT.is_dir():
            shutil.rmtree(OUTPUT)
        else:
            OUTPUT.unlink()

    OUTPUT.mkdir(parents=True)
    for relative in PUBLIC_FILES:
        source = ROOT / relative
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    (OUTPUT / "en").mkdir(parents=True, exist_ok=True)
    shutil.copy2(english, OUTPUT / "en" / "index.html")
    shutil.copytree(assets, OUTPUT / "assets")

    print("Packaged Cloudflare Pages site into dist/ (repository docs and tooling excluded).")


if __name__ == "__main__":
    main()
