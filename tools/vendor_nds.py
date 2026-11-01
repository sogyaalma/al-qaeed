#!/usr/bin/env python3
"""Pinned NDS vendor integration (NDS IQ §Install, reproducible provenance).

One command per stage, no hidden state:

  python3 tools/vendor_nds.py fetch    # download the pinned tag into .nds/ (NDS_ROOT, gitignored)
  python3 tools/vendor_nds.py sync     # compile CSS + copy the runtime into assets/, write the manifest
  python3 tools/vendor_nds.py verify   # offline: banners and hashes still match docs/nds-assets.json
  python3 tools/vendor_nds.py status   # print the pin, the installed root and the asset banners

The pin lives in tools/nds-pin.json. `fetch` refuses to install a tag whose
commit does not match the pin, so the runtime can never drift silently.

Provenance model (see docs/NDS-INTEGRATION.md):
  * JavaScript bundles are the upstream-committed build outputs at the pinned
    tag, copied byte for byte (`assets/js/*.min.js` in the NDS repository are
    produced by _plugins/js_processor.rb and committed, not built by Jekyll).
  * CSS bundles are compiled here from the pinned tag's own SCSS with Dart Sass
    (npm `sass`) because the Jekyll/Ruby toolchain and the release ZIP are not
    available in this environment. The compile reproduces Jekyll's documented
    settings (`sass.style: compressed`, `sass_dir: _sass`) and the
    _plugins/css_banner_format.rb banner newline fix.
  * The head's inline first-paint gate is compiled from _sass/_fold.scss with
    `$inline: true`, exactly like _includes/critical-inline.html, so the gate can
    never drift from the critical bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PIN_FILE = ROOT / "tools" / "nds-pin.json"
NDS_ROOT = ROOT / ".nds"
ASSETS = ROOT / "assets"
GENERATED = ROOT / "tools" / "generated"
MANIFEST = ROOT / "docs" / "nds-assets.json"

PIN = json.loads(PIN_FILE.read_text(encoding="utf-8"))
VERSION = PIN["runtime_version_banner"]

# Entry stylesheets shipped in the tag's assets/css/ (Jekyll compiles these).
CSS_BUNDLES = (
    "nds.critical.min",
    "nds-main.min",
    "nds-icons.min",
    "nds-accessibility.min",
    "hgi-rounded-stroke-min",
)

# Bundles the v1.12.0 runtime ships. Everything else in assets/js/ is stale.
JS_BUNDLES = (
    "nds-main.min.js",
    "nds-accessibility.min.js",
    "nds-delegated.min.js",
    "nds-extras.min.js",
    "nds-audit.min.js",
)

# Bundles inherited from the pre-1.12 development build. v1.12.0 folded chart,
# code, editor, date-picker, autocomplete, ipv, export and upload into
# nds-extras.min.js, and cookie consent into nds-main.min.js (nds-cookies.js).
OBSOLETE_JS = (
    "nds-chart.min.js",
    "nds-code.min.js",
    "nds-cookie-consent.min.js",
    "nds-editor.min.js",
)

# Fallback font extracted for the pre-1.12 build's data: URI @font-face.
# v1.12.0 references ../fonts/hgi-stroke-rounded.woff2 instead; no data: URI
# font remains, so the CSP workaround file is obsolete.
OBSOLETE_FONTS = ("hgi-blank.woff2",)

# Files inside assets/ that belong to the project, not to the pinned release, so
# the vendor manifest never claims a hash for them:
#   theme.css — the project's stylesheet theme (components/themes.md), reviewed in
#               docs/CUSTOM-EXCEPTIONS.md
#   site.js   — the project's own routing module
PROJECT_OWNED_ASSETS = frozenset({"assets/css/theme.css", "assets/js/site.js"})

# Canonical chrome includes copied out of the tag so the offline site build never
# hand-copies upstream markup: {upstream file: generated file}.
GENERATED_INCLUDES = {
    "accessibility-panel.html": "nds-accessibility-panel.html",
}

# NDS IQ §Install step 3: the readable twin an agent consults instead of the
# minified bundles.
SOURCE_DIRS = (
    "_js", "_sass", "_includes", "_layouts", "_data",
    "components", "utilities", "layout", "ui-shell", "core",
    "templates", "examples", "guides", "events",
)

# Government identity assets that a personal site must not ship
# (owner decision recorded in NDS-PLAN.md). Everything under the tag's
# assets/img/, assets/icon/ and assets/docs-assets/ is therefore NOT copied.
EXCLUDED_UPSTREAM_ASSETS = (
    "assets/img/", "assets/icon/", "docs-assets/",
)


def log(message: str) -> None:
    print(message, flush=True)


def die(message: str) -> "SystemExit":
    return SystemExit(f"vendor_nds: {message}")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def http_get(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "al-qaeed-vendor-tool"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


# ── fetch ────────────────────────────────────────────────────────────────────

def resolve_tag_commit() -> str:
    """Return the commit the pinned tag points at, dereferencing annotated tags."""
    payload = json.loads(http_get(PIN["source_of_truth"]["tag_api"]).decode("utf-8"))
    obj = payload["object"]
    if obj["type"] == "commit":
        return obj["sha"]
    if obj["type"] == "tag":
        detail = json.loads(http_get(obj["url"]).decode("utf-8"))
        return detail["object"]["sha"]
    raise die(f"unexpected tag object type {obj['type']!r}")


def install_source_tree(tarball: bytes, destination: pathlib.Path) -> str:
    """Extract the tag tarball flat into destination; return the wrapper name."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        members = archive.getmembers()
        wrappers = {m.name.split("/", 1)[0] for m in members}
        if len(wrappers) != 1:
            raise die(f"tarball has no single top-level folder: {sorted(wrappers)[:5]}")
        wrapper = wrappers.pop()
        for member in members:
            # Guard against absolute paths / traversal before extracting.
            if member.name.startswith("/") or ".." in pathlib.PurePosixPath(member.name).parts:
                raise die(f"unsafe tar member: {member.name}")
            if member.issym() or member.islnk():
                raise die(f"refusing to extract link member: {member.name}")
        # `filter='data'` exists from CPython 3.11.4/3.12; the manual guard above
        # covers older interpreters.
        try:
            archive.extractall(destination, members=members, filter="data")
        except TypeError:
            archive.extractall(destination, members=members)
    return wrapper


def populate_source_twin() -> None:
    """Create .nds/_source/ (NDS IQ §Install step 3) from the installed root."""
    twin = NDS_ROOT / "_source"
    if twin.exists():
        shutil.rmtree(twin)
    twin.mkdir(parents=True)
    copied = []
    for name in SOURCE_DIRS:
        src = NDS_ROOT / name
        if not src.is_dir():
            continue
        shutil.copytree(src, twin / name, symlinks=False)
        copied.append(name)
    log(f"  _source/ populated: {', '.join(copied)}")


def cmd_fetch(force: bool) -> None:
    if NDS_ROOT.exists() and not force:
        provenance = NDS_ROOT / "PROVENANCE.json"
        if provenance.is_file():
            recorded = json.loads(provenance.read_text(encoding="utf-8"))
            if recorded.get("commit") == PIN["commit"] and (NDS_ROOT / "_source").is_dir():
                log(f".nds/ already holds {PIN['tag']} @ {PIN['commit'][:12]} (use --force to reinstall)")
                return
        raise die(".nds/ exists without matching provenance; rerun with --force")

    commit = resolve_tag_commit()
    if commit != PIN["commit"]:
        raise die(
            f"tag {PIN['tag']} resolves to {commit}, pin says {PIN['commit']}. "
            "Refusing to install. Update tools/nds-pin.json deliberately after "
            "reading the release changelog and migration notes."
        )
    log(f"tag {PIN['tag']} → commit {commit} (matches pin)")

    tarball = http_get(PIN["source_of_truth"]["tarball"], timeout=600)
    digest = hashlib.sha256(tarball).hexdigest()
    log(f"downloaded {len(tarball)} bytes, sha256 {digest}")

    if NDS_ROOT.exists():
        shutil.rmtree(NDS_ROOT)
    with tempfile.TemporaryDirectory() as staging:
        wrapper = install_source_tree(tarball, pathlib.Path(staging))
        shutil.move(str(pathlib.Path(staging) / wrapper), str(NDS_ROOT))

    # NDS IQ: the root is correct when _site/ resolves directly; this release's
    # built twin ships only inside the release ZIP, which this environment
    # cannot reach. Record that honestly instead of faking the folder.
    populate_source_twin()

    (NDS_ROOT / "PROVENANCE.json").write_text(
        json.dumps(
            {
                "repo": PIN["repo"],
                "tag": PIN["tag"],
                "commit": commit,
                "released": PIN["released"],
                "tarball_url": PIN["source_of_truth"]["tarball"],
                "tarball_sha256": digest,
                "site_twin": "absent — release ZIP host (objects.githubusercontent.com) is not reachable here",
                "source_twin": "_source/ populated from the same tag",
                "installed_by": "tools/vendor_nds.py fetch",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    banner = read_js_banner(NDS_ROOT / "assets" / "js" / "nds-main.min.js")
    if banner != VERSION:
        raise die(f"installed runtime banner says {banner!r}, pin says {VERSION!r}")
    log(f".nds/ installed at {PIN['tag']} (runtime banner {banner})")


# ── compile ──────────────────────────────────────────────────────────────────

def site_config() -> dict:
    """Minimal _config.yml reader (flat scalars only — enough for the banners)."""
    config = {}
    for line in (NDS_ROOT / "_config.yml").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z_][\w]*):\s*(.+?)\s*(?:#.*)?$", line)
        if match:
            config[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return config


def prepare_entry_scss(workdir: pathlib.Path) -> None:
    """Strip front matter and resolve the Liquid banner vars in the entry SCSS."""
    config = site_config()
    values = {
        "site.version": config.get("version", VERSION),
        "site.license": config.get("license", PIN["license"]),
        "site.repository_url": f"https://github.com/{PIN['repo']}",
        "site.author": config.get("author", ""),
        "site.author_profile": config.get("author_profile", ""),
    }
    if values["site.version"] != VERSION:
        raise die(
            f"_config.yml version {values['site.version']!r} != pinned banner {VERSION!r}"
        )
    for name in CSS_BUNDLES:
        source = NDS_ROOT / "assets" / "css" / f"{name}.scss"
        if not source.is_file():
            raise die(f"missing entry stylesheet in the pinned tag: {source}")
        text = source.read_text(encoding="utf-8")
        text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
        for key, value in values.items():
            text = text.replace("{{ %s }}" % key, value).replace("{{%s}}" % key, value)
        leftover = re.findall(r"{{.*?}}|{%-?.*?-?%}", text)
        if leftover:
            raise die(f"unresolved Liquid in {source.name}: {leftover[:3]}")
        (workdir / f"{name}.scss").write_text(text, encoding="utf-8")
    # _includes/critical-inline.html compiles the shared fold block inline.
    (workdir / "nds-fold-inline.scss").write_text(
        '@use "fold" with ($inline: true);\n', encoding="utf-8"
    )


def sass_binary() -> list[str]:
    local = ROOT / "node_modules" / ".bin" / "sass"
    if local.exists():
        return [str(local)]
    found = shutil.which("sass")
    if found:
        return [found]
    raise die(
        "Dart Sass not found. Run `npm ci` (devDependency `sass`) so the NDS CSS "
        "bundles can be compiled from the pinned tag."
    )


def compile_css(workdir: pathlib.Path, outdir: pathlib.Path) -> dict[str, pathlib.Path]:
    binary = sass_binary()
    outdir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name in list(CSS_BUNDLES) + ["nds-fold-inline"]:
        target = outdir / f"{name}.css"
        command = binary + [
            "--no-source-map",
            "--style=compressed",
            "--quiet",
            "--quiet-deps",
            f"--load-path={NDS_ROOT / '_sass'}",
            f"--load-path={workdir}",
            str(workdir / f"{name}.scss"),
            str(target),
        ]
        result = subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT))
        if result.returncode != 0:
            raise die(f"sass failed for {name}:\n{result.stderr[-2000:]}")
        if result.stderr.strip():
            log(f"  sass warnings for {name}: {result.stderr.strip()[:400]}")
        outputs[name] = target
    return outputs


def postprocess_css(data: bytes) -> bytes:
    """Byte-level fixes only; no component rule is rewritten.

    1. Drop a leading UTF-8 BOM. Dart Sass copies the BOM that opens
       _sass/_hgiRoundedStroke.scss into the compiled sheet; upstream's own
       pipeline ships it too, and a BOM at byte 0 is harmless, but the project
       keeps vendor CSS byte-clean so hashes and diffs stay readable.
    2. Separate the leading /*! banner from the first rule — the exact fix
       _plugins/css_banner_format.rb applies after a Jekyll build.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return re.sub(rb"(/\*!.*?\*/)(?!\n)", rb"\1\n", data, count=1, flags=re.S)


def read_css_banner(path: pathlib.Path) -> str | None:
    head = path.read_text(encoding="utf-8", errors="replace")[:600]
    match = re.search(r"\*\s*Version:\s*([0-9][^\s*]*)", head)
    return match.group(1) if match else None


def read_js_banner(path: pathlib.Path) -> str | None:
    head = path.read_text(encoding="utf-8", errors="replace")[:600]
    match = re.search(r"\*\s*Version:\s*([0-9][^\s*]*)", head)
    return match.group(1) if match else None


# ── sync ─────────────────────────────────────────────────────────────────────

def require_root() -> None:
    provenance = NDS_ROOT / "PROVENANCE.json"
    if not provenance.is_file():
        raise die("NDS_ROOT (.nds/) is not installed — run `python3 tools/vendor_nds.py fetch`")
    recorded = json.loads(provenance.read_text(encoding="utf-8"))
    if recorded.get("commit") != PIN["commit"] or recorded.get("tag") != PIN["tag"]:
        raise die(
            f".nds/ holds {recorded.get('tag')} @ {recorded.get('commit')}, pin says "
            f"{PIN['tag']} @ {PIN['commit']}"
        )
    if not (NDS_ROOT / "_source").is_dir():
        raise die(".nds/_source/ is missing — rerun fetch so the readable twin exists")


def cmd_sync() -> dict:
    require_root()
    sass_version = subprocess.run(
        sass_binary() + ["--version"], capture_output=True, text=True, cwd=str(ROOT)
    ).stdout.strip()
    log(f"compiling NDS CSS with {sass_version}")

    with tempfile.TemporaryDirectory() as staging:
        workdir = pathlib.Path(staging) / "scss"
        workdir.mkdir()
        prepare_entry_scss(workdir)
        outputs = compile_css(workdir, pathlib.Path(staging) / "css")

        css_dir = ASSETS / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        for name in CSS_BUNDLES:
            data = postprocess_css(outputs[name].read_bytes())
            (css_dir / f"{name}.css").write_bytes(data)
            log(f"  assets/css/{name}.css  {len(data):,} bytes")

        GENERATED.mkdir(parents=True, exist_ok=True)
        fold = postprocess_css(outputs["nds-fold-inline"].read_bytes())
        (GENERATED / "nds-fold-inline.css").write_bytes(fold)
        log(f"  tools/generated/nds-fold-inline.css  {len(fold):,} bytes (inline head gate)")

    # Chrome includes the pages copy verbatim. Materialised here so the site build
    # stays offline and an NDS upgrade moves them without a hand edit in build.py.
    for source_name, generated_name in GENERATED_INCLUDES.items():
        source = NDS_ROOT / "_source" / "_includes" / source_name
        if not source.is_file():
            raise die(f"pinned tag does not ship _includes/{source_name}")
        shutil.copyfile(source, GENERATED / generated_name)
        log(f"  tools/generated/{generated_name}  {source.stat().st_size:,} bytes (canonical include)")

    # Runtime JavaScript: byte-identical copies of the tag's committed bundles.
    js_dir = ASSETS / "js"
    js_dir.mkdir(parents=True, exist_ok=True)
    for name in JS_BUNDLES:
        source = NDS_ROOT / "assets" / "js" / name
        if not source.is_file():
            raise die(f"pinned tag does not ship assets/js/{name}")
        shutil.copyfile(source, js_dir / name)
        log(f"  assets/js/{name}  {source.stat().st_size:,} bytes (copied)")

    removed = []
    for name in OBSOLETE_JS:
        stale = js_dir / name
        if stale.exists():
            stale.unlink()
            removed.append(f"assets/js/{name}")
    for name in OBSOLETE_FONTS:
        stale = ASSETS / "fonts" / name
        if stale.exists():
            stale.unlink()
            removed.append(f"assets/fonts/{name}")
    stale_i18n = ASSETS / "i18n" / "ar.json"
    if stale_i18n.is_file():
        stale_i18n.unlink()
        removed.append("assets/i18n/ar.json (pre-1.12 flat dictionary)")
    if removed:
        log("  removed stale inherited files:\n    " + "\n    ".join(removed))

    # Fonts and per-component i18n ship unchanged from the tag.
    fonts_target = ASSETS / "fonts"
    fonts_target.mkdir(parents=True, exist_ok=True)
    for source in sorted((NDS_ROOT / "assets" / "fonts").glob("*")):
        if source.is_file():
            shutil.copyfile(source, fonts_target / source.name)
    i18n_target = ASSETS / "i18n"
    if i18n_target.exists():
        shutil.rmtree(i18n_target)
    shutil.copytree(NDS_ROOT / "assets" / "i18n", i18n_target)
    log("  assets/fonts/ and assets/i18n/ refreshed from the pinned tag")

    license_source = NDS_ROOT / "LICENSE"
    if license_source.is_file():
        (ASSETS / "licenses" / "NDS-vanilla-MIT.txt").write_bytes(license_source.read_bytes())
        (ROOT / "docs" / "LICENSE-NDS-vanilla.txt").write_bytes(license_source.read_bytes())
        log("  NDS MIT license text refreshed")

    # Government imagery is deliberately not copied; the project favicon stays.
    log("  skipped upstream assets: " + ", ".join(EXCLUDED_UPSTREAM_ASSETS) + " (owner identity)")

    return write_manifest(sass_version, removed)


def banner_check() -> dict[str, str | None]:
    banners = {}
    for name in CSS_BUNDLES:
        path = ASSETS / "css" / f"{name}.css"
        banners[f"assets/css/{name}.css"] = read_css_banner(path) if path.is_file() else None
    for name in JS_BUNDLES:
        path = ASSETS / "js" / name
        banners[f"assets/js/{name}"] = read_js_banner(path) if path.is_file() else None
    return banners


def write_manifest(sass_version: str, removed: list[str]) -> dict:
    banners = banner_check()
    mismatched = {k: v for k, v in banners.items() if v not in (None, VERSION)}
    if mismatched:
        raise die(f"banner mismatch (NDS IQ P5 — mixed release): {mismatched}")
    unbannered = sorted(k for k, v in banners.items() if v is None)

    files = {}
    for path in sorted(ASSETS.rglob("*")):
        if not path.is_file() or path.name == "README.md":
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in PROJECT_OWNED_ASSETS or relative.startswith("assets/img/") or relative.startswith("assets/docs/"):
            continue  # project-owned assets are tracked by the site, not by NDS
        files[relative] = sha256(path)
    generated = {
        "tools/generated/nds-fold-inline.css": sha256(GENERATED / "nds-fold-inline.css")
    }
    for generated_name in GENERATED_INCLUDES.values():
        path = GENERATED / generated_name
        if not path.is_file():
            raise die(f"generated include missing: {path}")
        generated[f"tools/generated/{generated_name}"] = sha256(path)

    provenance = json.loads((NDS_ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    manifest = {
        "pinned_release": PIN["tag"],
        "pinned_commit": PIN["commit"],
        "released": PIN["released"],
        "runtime_banner": VERSION,
        "repository": f"https://github.com/{PIN['repo']}",
        "license": PIN["license"],
        "source": {
            "installed_from": provenance["tarball_url"],
            "tarball_sha256": provenance["tarball_sha256"],
            "nds_root": ".nds/ (gitignored; reinstall with `python3 tools/vendor_nds.py fetch`)",
            "release_zip": PIN["source_of_truth"]["release_asset"],
            "release_zip_status": PIN["source_of_truth"]["release_asset_status"],
            "built_site_twin": provenance["site_twin"],
        },
        "build": {
            "javascript": "byte-identical copies of the tag's committed assets/js/*.min.js",
            "css": f"compiled from the tag's SCSS with {sass_version} (style=compressed, sass_dir=_sass), BOM stripped, banner newline fix from _plugins/css_banner_format.rb",
            "inline_head_gate": "compiled from _sass/_fold.scss with $inline:true, as _includes/critical-inline.html does",
            "tool": "tools/vendor_nds.py sync",
        },
        "bundles_without_version_banner": unbannered,
        "removed_inherited_files": removed,
        "not_copied_from_upstream": list(EXCLUDED_UPSTREAM_ASSETS),
        "sha256": files,
        "generated_sha256": generated,
        "distribution_excluded_fonts": [
            "assets/fonts/Maqroo-Regular.woff2",
            "assets/fonts/SaudiWeb-Bold.woff2",
            "assets/fonts/SaudiWeb-Regular.woff2",
        ],
        "distribution_note": "tools/package.py drops the excluded fonts and their @font-face rules (font licensing review). See tools/font_policy.py.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"manifest written: {MANIFEST.relative_to(ROOT)} ({len(files)} asset hashes)")
    if unbannered:
        log("  no Version: banner (documented, not inferred): " + ", ".join(unbannered))
    return manifest


# ── verify / status ──────────────────────────────────────────────────────────

def cmd_verify() -> int:
    if not MANIFEST.is_file():
        raise die("docs/nds-assets.json is missing — run sync first")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    if manifest.get("pinned_commit") != PIN["commit"]:
        problems.append(f"manifest commit {manifest.get('pinned_commit')} != pin {PIN['commit']}")
    for relative, digest in manifest.get("sha256", {}).items():
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"missing asset {relative}")
        elif sha256(path) != digest:
            problems.append(f"asset drift: {relative}")
    for relative, digest in manifest.get("generated_sha256", {}).items():
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"missing generated file {relative}")
        elif sha256(path) != digest:
            problems.append(f"generated drift: {relative}")
    for name, banner in banner_check().items():
        if banner not in (None, VERSION):
            problems.append(f"banner {name} says {banner!r}, expected {VERSION!r} or none")
    if problems:
        print("FAIL vendor verification")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"PASS vendor verification — {PIN['tag']} @ {PIN['commit'][:12]}, "
          f"{len(manifest.get('sha256', {}))} assets, banners consistent")
    return 0


def cmd_status() -> None:
    log(f"pin: {PIN['tag']} @ {PIN['commit']}")
    provenance = NDS_ROOT / "PROVENANCE.json"
    if provenance.is_file():
        recorded = json.loads(provenance.read_text(encoding="utf-8"))
        log(f"NDS_ROOT: installed {recorded.get('tag')} @ {recorded.get('commit')}")
        log(f"          built twin: {recorded.get('site_twin')}")
    else:
        log("NDS_ROOT: not installed (run `python3 tools/vendor_nds.py fetch`)")
    for name, banner in banner_check().items():
        log(f"  {name}: {banner or 'no Version: banner'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "sync", "verify", "status"))
    parser.add_argument("--force", action="store_true", help="reinstall .nds/ even when provenance matches")
    args = parser.parse_args()
    if args.command == "fetch":
        cmd_fetch(args.force)
    elif args.command == "sync":
        cmd_sync()
        sys.exit(cmd_verify())
    elif args.command == "verify":
        sys.exit(cmd_verify())
    else:
        cmd_status()


if __name__ == "__main__":
    main()
