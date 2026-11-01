#!/usr/bin/env python3
"""Package only public static-site files for Cloudflare Pages.

Run after tools/build.py:
  python3 tools/build.py && python3 tools/package.py

The generated dist/ directory deliberately excludes repository documentation,
tests, source content and build tooling. It does include the generated
/nds-showcase/ review route, which is published with `noindex` and kept out of the
public navigation and the sitemap.
"""
import pathlib
import shutil

from font_policy import BLOCKED, apply_to_package, validate_assets

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist"
PUBLIC_FILES = ("index.html", "404.html", "robots.txt", "sitemap.xml", "_headers")
PUBLIC_DIRS = ("en", "nds-showcase")


def main():
    # Validate inputs before replacing a previous package.
    for relative in PUBLIC_FILES:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Required public file is missing: {relative}")
    for relative in PUBLIC_DIRS:
        if not (ROOT / relative / "index.html").is_file():
            raise SystemExit(f"Required public directory is missing: {relative}/ (run tools/build.py)")
    assets = ROOT / "assets"
    if not assets.is_dir():
        raise SystemExit("Required public directory is missing: assets/")

    # Reject links before touching an existing output: copytree follows them by
    # default and could accidentally publish private files outside the repository.
    inputs = [ROOT / name for name in PUBLIC_FILES] + [assets]
    for relative in PUBLIC_DIRS:
        directory = ROOT / relative
        inputs.append(directory)
        inputs.extend(path for path in directory.rglob("*"))
    inputs.extend(assets.rglob("*"))
    for source in inputs:
        if source.is_symlink():
            raise SystemExit(f"Refusing to package symlink: {source.relative_to(ROOT)}")

    try:
        validate_assets(assets)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

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

    for relative in PUBLIC_DIRS:
        shutil.copytree(ROOT / relative, OUTPUT / relative)

    shutil.copytree(assets, OUTPUT / "assets", ignore=lambda directory, names: BLOCKED if pathlib.Path(directory) == assets / 'fonts' else ())
    apply_to_package(OUTPUT / 'assets')

    published = sum(1 for path in OUTPUT.rglob("*") if path.is_file())
    print(f"Packaged Cloudflare Pages site into dist/ ({published} files; repository docs and tooling excluded).")


if __name__ == "__main__":
    main()
