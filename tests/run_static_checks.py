#!/usr/bin/env python3
"""Dependency-free checks for the generated Cloudflare Pages package.

Run after: python3 tools/build.py && python3 tools/package.py
"""
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import sys
from urllib.parse import urlsplit, unquote
import base64
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS {name}" + (f" [{detail}]" if detail else ""))
    else:
        failed += 1
        print(f"FAIL {name}" + (f" [{detail}]" if detail else ""))


class Markup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: List[Tuple[str, Dict[str, Optional[str]]]] = []
        self.html_attrs: Dict[str, Optional[str]] = {}
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        values = dict(attrs)
        self.tags.append((tag, values))
        if tag == "html":
            self.html_attrs = values
        elif tag == "h1":
            self.h1_count += 1

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)


def read_markup(path: Path) -> Markup:
    parser = Markup()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def local_file(path: str, base: Path = DIST / "index.html") -> Optional[Path]:
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        return None
    route = unquote(parsed.path)
    if not route:
        return base
    if not route.startswith("/"):
        return (base.parent / route).resolve()
    if route == "/":
        route = "/index.html"
    elif route.endswith("/"):
        route += "index.html"
    return DIST / route.lstrip("/")


if not DIST.is_dir():
    print("FAIL dist/ does not exist; run tools/build.py and tools/package.py first.")
    sys.exit(1)

# Build/package parity ensures the browser preview receives the generated files.
public_files = ("index.html", "en/index.html", "404.html", "robots.txt", "sitemap.xml", "_headers")
for relative in public_files:
    source, output = ROOT / relative, DIST / relative
    check(f"dist contains {relative}", source.is_file() and output.is_file())
    if source.is_file() and output.is_file():
        check(f"dist copy matches {relative}", source.read_bytes() == output.read_bytes())

manifest = json.loads((ROOT / 'docs/nds-assets.json').read_text())
policy_exceptions = set(manifest['distribution_excluded_fonts']) | set(manifest['distribution_sha256'])
asset_files = sorted(path for path in (ROOT / "assets").rglob("*") if path.is_file() and path.relative_to(ROOT).as_posix() not in policy_exceptions)
missing_or_different = [
    path.relative_to(ROOT).as_posix()
    for path in asset_files
    if not (DIST / path.relative_to(ROOT)).is_file()
    or path.read_bytes() != (DIST / path.relative_to(ROOT)).read_bytes()
]
check("assets outside explicit font-policy exceptions are copied byte-for-byte", not missing_or_different,
      ", ".join(missing_or_different[:5]) or f"{len(asset_files)} assets")

pages = {
    "Arabic route": (DIST / "index.html", "ar", "rtl"),
    "English route": (DIST / "en/index.html", "en", "ltr"),
}
for label, (path, lang, direction) in pages.items():
    if not path.is_file():
        continue
    markup = read_markup(path)
    check(f"{label} has lang={lang} and dir={direction}",
          markup.html_attrs.get("lang") == lang and markup.html_attrs.get("dir") == direction)
    check(f"{label} has exactly one h1", markup.h1_count == 1, f"h1={markup.h1_count}")

    hrefs = [attrs.get("href", "") for tag, attrs in markup.tags if tag == "link"]
    check(f"{label} preloads NDS critical and main CSS",
          any("nds.critical.min.css" in (href or "") for href in hrefs)
          and any("nds-main.min.css" in (href or "") for href in hrefs)
          and any("theme.css" in (href or "") for href in hrefs), str(hrefs[:8]))
    check(f"{label} loads the NDS runtime script",
          any(tag == "script" and attrs.get("src") and "nds-main.min.js" in attrs.get("src", "")
              for tag, attrs in markup.tags))
    check(f"{label} has no inline style attributes",
          not any("style" in attrs for _, attrs in markup.tags))

    referenced: List[str] = []
    for tag, attrs in markup.tags:
        for key in ("href", "src", "poster"):
            value = attrs.get(key)
            if value:
                referenced.append(value)
        for key in ("srcset", "imagesrcset"):
            value = attrs.get(key)
            if value:
                referenced.extend(candidate.strip().split()[0]
                                  for candidate in value.split(",") if candidate.strip())
    missing = []
    for value in referenced:
        candidate = local_file(value)
        if candidate is not None and not candidate.is_file():
            missing.append(value)
    check(f"{label} local HTML references resolve in dist", not missing,
          ", ".join(sorted(set(missing))[:8]) or f"{len(referenced)} references scanned")

    check(f"{label} uses NDS layout landmarks",
          "nds-main-nav" in path.read_text(encoding="utf-8")
          and "nds-content" in path.read_text(encoding="utf-8"))

# The 404 route is a generated page too and uses the same NDS chrome.
not_found = DIST / "404.html"
check("dist contains generated 404.html", not_found.is_file())
if not_found.is_file():
    markup = read_markup(not_found)
    hrefs = [attrs.get("href", "") for tag, attrs in markup.tags if tag == "link"]
    check("404 preloads NDS CSS",
          any("nds.critical.min.css" in (href or "") for href in hrefs)
          and any("nds-main.min.css" in (href or "") for href in hrefs), str(hrefs[:8]))
    check("404 loads the NDS runtime script",
          any(tag == "script" and attrs.get("src") and "nds-main.min.js" in attrs.get("src", "")
              for tag, attrs in markup.tags))

theme_path = DIST / "assets/css/theme.css"
critical_path = DIST / "assets/css/nds.critical.min.css"
check("NDS critical CSS is packaged", critical_path.is_file())
check("project theme overrides are packaged", theme_path.is_file())
if theme_path.is_file():
    theme = theme_path.read_text(encoding="utf-8")
    check("theme rebinds semantic tokens without editing NDS bundles",
          "--background-body" in theme and "--background-primary" in theme)

# CSS URLs are local files, not remote runtime dependencies.
css_missing: List[str] = []
for css_path in sorted((DIST / "assets/css").glob("*.css")):
    for value in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css_path.read_text(encoding="utf-8")):
        candidate = local_file(value[1], css_path)
        if candidate is not None and not candidate.is_file():
            css_missing.append(f"{css_path.name}: {value[1]}")
check("all local CSS url() assets resolve in dist", not css_missing,
      ", ".join(css_missing[:8]) or "all local URLs resolved")

headers = (DIST / "_headers").read_text(encoding="utf-8") if (DIST / "_headers").is_file() else ""
check("Cloudflare security headers and same-origin CSP are packaged",
      "Content-Security-Policy:" in headers
      and "style-src 'self'" in headers and "script-src 'self'" in headers
      and "default-src 'self'" in headers)

# Guard against the regressions missed by the original 35-check suite.
all_markup = {name: read_markup(DIST / name) for name in ("index.html", "en/index.html", "404.html")}
for name, markup in all_markup.items():
    path = DIST / name
    ids = [attrs["id"] for _, attrs in markup.tags if attrs.get("id")]
    check(f"{name} unique IDs", len(ids) == len(set(ids)))
    missing_anchors = []
    for tag, attrs in markup.tags:
        if tag != "a" or not attrs.get("href"):
            continue
        href = attrs["href"]
        parsed = urlsplit(href)
        dest = local_file(href, path)
        if dest is None:
            continue
        if not dest.is_file():
            missing_anchors.append(href)
        elif parsed.fragment:
            target = read_markup(dest)
            if not any(a.get("id") == unquote(parsed.fragment) for _, a in target.tags):
                missing_anchors.append(href)
    check(f"{name} all local links and fragments resolve without JS", not missing_anchors, str(missing_anchors))
    text = path.read_text(encoding="utf-8")
    check(f"{name} no literal escaped newline in content", "\\n" not in text)
    check(f"{name} exactly one main", sum(tag == "main" for tag, _ in markup.tags) == 1)
    for tag, directive in (("script", "script-src"), ("style", "style-src")):
        body_hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode() + "'"
                       for m in re.finditer(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", text, re.S) if m.group(1).strip()]
        policy = re.search(rf"(?:^|; )?{directive} ([^;]+)", headers).group(1)
        check(f"{name} exact inline {tag} bodies authorized by CSP", all(h in policy for h in body_hashes))

script_policy = re.search(r"script-src ([^;]+)", headers).group(1)
style_policy = re.search(r"style-src ([^;]+)", headers).group(1)
check("CSP forbids arbitrary inline scripts/styles and eval", "'unsafe-inline'" not in script_policy
      and "'unsafe-eval'" not in headers and "'unsafe-inline'" not in style_policy
      and "script-src-attr 'none'" in headers and "object-src 'none'" in headers)
vercel = json.loads((ROOT / "vercel.json").read_text())
vercel_csp = next(h['value'] for rule in vercel['headers'] for h in rule['headers'] if h['key'] == 'Content-Security-Policy')
check("optional Vercel CSP matches Cloudflare", vercel_csp == headers.split('Content-Security-Policy: ', 1)[1].splitlines()[0])
check("unfingerprinted Vercel assets are not immutable", 'immutable' not in json.dumps(vercel))
check("dist excludes private source/tooling", all(p.name in {'index.html','en','404.html','robots.txt','sitemap.xml','_headers','assets'} for p in DIST.iterdir()))
check("dist contains no symlinks", not any(p.is_symlink() for p in DIST.rglob('*')))
check("main CSS has no misplaced BOM", b'\xef\xbb\xbf' not in (DIST / 'assets/css/nds-main.min.css').read_bytes())
check("HGI lazy stylesheet and fallback font exist", (DIST / 'assets/css/hgi-rounded-stroke-min.css').is_file() and (DIST / 'assets/fonts/hgi-blank.woff2').is_file())
site_url = json.loads((ROOT / 'content/content.json').read_text())['site']['url'].rstrip('/')
xml = ET.parse(DIST / 'sitemap.xml')
locations = [el.text for el in xml.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
check("sitemap contains only both canonical language routes", locations == [site_url+'/', site_url+'/en/'])
check("robots points at configured sitemap", f'Sitemap: {site_url}/sitemap.xml' in (DIST / 'robots.txt').read_text())
check("no runtime JS dependencies in npm manifest", not json.loads((ROOT / 'package.json').read_text()).get('dependencies'))

hgi_css = (DIST / 'assets/css/hgi-rounded-stroke-min.css').read_text()
hgi_names = {name for markup in all_markup.values() for _, attrs in markup.tags
             for cls in attrs.get('class', '').split() if cls.startswith('hgi-') and cls != 'hgi-stroke'
             for name in [cls]}
check("all authored HGI font icon classes have generated CSS rules", all('.hgi-stroke.'+name+':before' in hgi_css for name in hgi_names))

manifest = json.loads((ROOT / 'docs/nds-assets.json').read_text())
changed_vendor = [name for name, digest in manifest['sha256'].items()
                  if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
check("vendored NDS inputs match reviewed artifact hashes", not changed_vendor, str(changed_vendor))
public_hashes = {name: digest for name, digest in manifest['sha256'].items()
                 if name not in manifest['distribution_excluded_fonts']}
public_hashes.update(manifest['distribution_sha256'])
changed_public = [name for name, digest in public_hashes.items()
                  if not (DIST / name).is_file() or hashlib.sha256((DIST / name).read_bytes()).hexdigest() != digest]
check("public NDS assets match reviewed distribution hashes", not changed_public, str(changed_public))
blocked = manifest['distribution_excluded_fonts']
check("fonts without redistribution grants are not published", all(not (DIST / name).exists() for name in blocked))
check("public CSS has no blocked font URLs", all(Path(name).name not in p.read_text() for name in blocked for p in (DIST / 'assets/css').glob('*.css')))

print(f"\n{passed}/{passed + failed} static checks passed")
sys.exit(1 if failed else 0)
