#!/usr/bin/env python3
"""Canonical NDS page chrome shared by every generated page.

Everything here is copied from the pinned NDS release (`.nds/_source/`, tag
v1.12.0) and only receives the four edits NDS IQ hard rule #3 allows: asset URL
rewrites, content replacement, documented modifier classes and CSP knob moves.

Sources (NDS IQ P3):
  _includes/head.html + head-inline-scripts.html + critical-inline.html  document head
  _sass/_fold.scss ($inline:true)     first-paint gate, compiled by tools/vendor_nds.py
  _includes/topbar.html               top bar widgets (showcase chrome only)
  ui-shell/mainnav.md                 main navigation
  ui-shell/hero.md + _includes/hero-sub.html   sub hero
  _includes/footer.html               footer
  _includes/accessibility-panel.html  accessibility FAB + panel (verbatim copy)
  _layouts/default.html               body order and runtime script tags
  components/themes.md                data-theme-toggle / brand seeds

The accessibility panel is read from the copy `tools/vendor_nds.py sync` puts in
tools/generated/, so an NDS upgrade moves it without a hand edit here.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
GENERATED = ROOT / "tools" / "generated"
PIN = json.loads((ROOT / "tools" / "nds-pin.json").read_text(encoding="utf-8"))

# Upstream site.asset_ver is "{version}.{short-sha}"; ours names the pinned tag
# commit so every asset URL carries its own provenance.
ASSET_VER = f"{PIN['runtime_version_banner']}.{PIN['commit'][:7]}"
ASSETS = "/assets"

# Project stylesheet theme (components/themes.md → Custom Palette / Stylesheet
# Themes). Render-blocking after the critical bundle, as head.html orders a brand
# stylesheet, so the owner's identity resolves before first paint.
THEME_CSS = f"{ASSETS}/css/theme.css"


def asset(path: str) -> str:
    """NDS IQ edit #1: rewrite a template asset URL to the project's asset root."""
    return f"{ASSETS}/{path.lstrip('/')}"


def versioned(path: str) -> str:
    return f"{asset(path)}?ver={ASSET_VER}"


# ── Liquid subset ────────────────────────────────────────────────────────────
# The generated include copies are upstream files, not templates we own. Only two
# constructs are resolved; anything else fails the build instead of leaking
# Liquid into a published page.

COMMENT = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", re.S)
IF_LANG = re.compile(
    r"\{%-?\s*if page\.lang == 'ar'\s*-?%\}(.*?)\{%-?\s*else\s*-?%\}(.*?)\{%-?\s*endif\s*-?%\}",
    re.S,
)
RELATIVE_URL = re.compile(r"\{\{\s*'([^']*)'\s*\|\s*relative_url\s*\}\}")

# NDS IQ edit class #2 (content): the upstream include links its own language
# routes. This project serves Arabic at / and English at /en/, so the two
# upstream routes are mapped instead of published as dead links.
ROUTE_MAP = {"/ar/": "/", "/ar": "/", "/en/": "/en/", "/en": "/en/", "/": "/"}


def resolve_include(text: str, lang: str) -> str:
    """Resolve the two Liquid constructs an upstream include uses for our pages."""
    text = COMMENT.sub("", text)
    text = IF_LANG.sub(lambda m: m.group(1) if lang == "ar" else m.group(2), text)
    text = RELATIVE_URL.sub(lambda m: ROUTE_MAP.get("/" + m.group(1).strip("/"), "/" + m.group(1).lstrip("/")), text)
    # A hard-coded upstream route in markup (the panel's language switch) is mapped
    # the same way.
    text = re.sub(r'href="(/ar/?|/en/?)(")', lambda m: 'href="' + ROUTE_MAP.get(m.group(1), m.group(1)) + m.group(2), text)
    leftover = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", text, re.S)
    if leftover:
        raise SystemExit(
            "unresolved Liquid in the generated NDS include (upstream changed shape):\n  "
            + "\n  ".join(part.strip()[:120] for part in leftover[:5])
        )
    return text.strip()


# Two deterministic corrections to the canonical panel, recorded as exceptions in
# docs/CUSTOM-EXCEPTIONS.md (#6, #7). Both are applied by the generator, never by
# hand, so an NDS upgrade re-applies them or fails loudly:
PANEL_FIELDSET = '<fieldset class="nds-form-group nds-switch-group">'
PANEL_LEGEND = (
    '<fieldset class="nds-form-group nds-switch-group">\n'
    '                                <legend class="nds-sr-only" data-i18n="section_modes">Accessibility Modes</legend>'
)
PANEL_PROGRESS_DIV = '<div class="nds-progress-circle">'
PANEL_PROGRESS_SPAN = '<span class="nds-progress-circle">'


def accessibility_panel(lang: str) -> str:
    """_includes/accessibility-panel.html, verbatim except two documented fixes."""
    source = GENERATED / "nds-accessibility-panel.html"
    if not source.is_file():
        raise SystemExit(
            f"{source} is missing — run `python3 tools/vendor_nds.py sync`"
        )
    markup = resolve_include(source.read_text(encoding="utf-8"), lang)

    # WCAG 2.1 H71: the mode switch group is a <fieldset> with no <legend>. The
    # release ships it that way, so the generator adds a visually hidden legend
    # carrying the component's own i18n key (assets/i18n/accessibility/*.json).
    if markup.count(PANEL_FIELDSET) != 1:
        raise SystemExit(
            "the canonical accessibility panel changed shape: expected exactly one "
            f"{PANEL_FIELDSET!r}; review docs/CUSTOM-EXCEPTIONS.md #6"
        )
    markup = markup.replace(PANEL_FIELDSET, PANEL_LEGEND, 1)

    # HTML content model: the reset button wraps its progress ring in a <div>,
    # which is not phrasing content. The ring is styled purely by its class
    # (_sass/components/_buttons.scss), so the element name changes and nothing else.
    if PANEL_PROGRESS_DIV not in markup:
        raise SystemExit(
            "the canonical accessibility panel changed shape: expected "
            f"{PANEL_PROGRESS_DIV!r}; review docs/CUSTOM-EXCEPTIONS.md #7"
        )
    markup = markup.replace(PANEL_PROGRESS_DIV, PANEL_PROGRESS_SPAN, 1)
    markup = markup.replace(
        "</svg>\n            </div>", "</svg>\n            </span>", 1
    )
    return markup


def inline_gate() -> str:
    """The canonical first-paint gate (_sass/_fold.scss compiled with $inline:true)."""
    path = GENERATED / "nds-fold-inline.css"
    if not path.is_file():
        raise SystemExit(f"{path} is missing — run `python3 tools/vendor_nds.py sync`")
    return path.read_text(encoding="utf-8").strip()


# ── head ─────────────────────────────────────────────────────────────────────

def head_scripts(theme_system_preference: bool = True) -> str:
    """_includes/head-inline-scripts.html, verbatim, plus one documented addition.

    The canonical script is copied byte for byte (one element, one CSP hash).
    NDS.Theme has no prefers-color-scheme surface, so the project adds a second,
    separate element that only acts when the visitor has no stored choice.
    Recorded in NDS-REPORT.md and docs/CUSTOM-EXCEPTIONS.md.
    """
    canonical = """<script>
    // Pre-paint FOUC guard: stamp saved data-theme before first paint, union-merged with markup/pack tokens so a stored value never clobbers them.
    (function() {
        var v = localStorage.getItem('nds-theme');
        if (v) {
            var d = document.documentElement;
            var t = ((d.getAttribute('data-theme') || '') + ' ' + v).split(/\\s+/)
                .filter(function (x, i, a) { return x && a.indexOf(x) === i; });
            d.setAttribute('data-theme', t.join(' '));
        }
    })();
    // Deferred styles: preload → injected stylesheet link (markers move with it). Rationale: ui-shell/head.md, CSP section.
    (function () {
        document.querySelectorAll('link[rel="preload"][data-nds-defer]').forEach(function (p) {
            var l = document.createElement('link');
            // Clone every attribute except rel/as — keeps href, fetchpriority, integrity, crossorigin, and the data-* markers.
            for (var i = 0; i < p.attributes.length; i++) {
                var a = p.attributes[i];
                if (a.name !== 'rel' && a.name !== 'as') l.setAttribute(a.name, a.value);
            }
            l.rel = 'stylesheet';
            p.removeAttribute('data-nds-defer');
            document.head.appendChild(l);
        });
    })();
</script>"""
    if not theme_system_preference:
        return canonical
    addition = """<script>
    // Project addition (docs/CUSTOM-EXCEPTIONS.md #2): NDS.Theme persists a manual
    // choice but has no OS-preference surface. Follow prefers-color-scheme only
    // while the visitor has nothing stored, using the canonical union merge.
    (function () {
      var stored;
      try { stored = localStorage.getItem('nds-theme'); } catch (e) { return; }
      if (stored || !window.matchMedia) return;
      if (!window.matchMedia('(prefers-color-scheme: dark)').matches) return;
      var d = document.documentElement;
      var t = ((d.getAttribute('data-theme') || '') + ' dark').split(/\\s+/)
        .filter(function (x, i, a) { return x && a.indexOf(x) === i; });
      d.setAttribute('data-theme', t.join(' '));
    })();
</script>"""
    return canonical + "\n    " + addition


def document_head(
    *,
    lang: str,
    direction: str,
    title: str,
    description: str,
    canonical_url: str | None = None,
    alternates: list[tuple[str, str]] | None = None,
    preload_image: str | None = None,
    extra_meta: str = "",
    jsonld: str = "",
    stylesheets: list[str] | None = None,
    head_extra: str = "",
) -> str:
    """The document head in _includes/head.html order.

    critical_inline mode (the release default for this project): the compiled
    fold gate paints first, the critical bundle is preloaded and applied by the
    head script, the project stylesheet theme is render-blocking after it, then
    main and the accessibility add-on are preloaded.
    """
    lines: list[str] = []
    lines.append("<!DOCTYPE html>")
    lines.append(f'<html lang="{lang}" dir="{direction}" data-palette>')
    lines.append("<head>")
    lines.append('  <meta charset="UTF-8">')
    lines.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f"  <title>{title}</title>")
    if description:
        lines.append(f'  <meta name="description" content="{description}">')
    if preload_image:
        lines.append(f'  <link rel="preload" as="image" href="{preload_image}" fetchpriority="high">')
    # Canonical inline first-paint gate (critical_inline: true).
    lines.append(f"  <style>{inline_gate()}</style>")
    lines.append(
        f'  <link rel="preload" href="{versioned("css/nds.critical.min.css")}" as="style" fetchpriority="high" data-nds-defer>'
    )
    # Project stylesheet theme: render-blocking after critical, as head.html does
    # for a brand stylesheet, so the identity resolves before paint.
    lines.append(
        f'  <link id="nds-theme-stylesheet" rel="stylesheet" href="{THEME_CSS}?ver={ASSET_VER}">'
    )
    lines.append(
        f'  <link rel="preload" href="{versioned("css/nds-main.min.css")}" as="style" fetchpriority="low" data-nds-defer="main">'
    )
    lines.append(
        f'  <link rel="preload" href="{versioned("css/nds-accessibility.min.css")}" as="style" fetchpriority="low" data-nds-defer>'
    )
    for sheet in stylesheets or []:
        lines.append(f'  <link rel="preload" href="{sheet}" as="style" data-nds-defer>')
    lines.append(f'  <link rel="icon" type="image/svg+xml" href="{asset("img/favicon.svg")}" fetchpriority="low">')
    if canonical_url:
        lines.append(f'  <link rel="canonical" href="{canonical_url}">')
    for hreflang, href in alternates or []:
        lines.append(f'  <link rel="alternate" hreflang="{hreflang}" href="{href}">')
    if extra_meta:
        lines.append(indent(extra_meta, 2))
    if jsonld:
        lines.append(indent(jsonld, 2))
    # Theme/brand stamp last so the resource preloads start first (head.html).
    for script in head_scripts().split("\n"):
        lines.append(f"  {script}" if script else "")
    if head_extra:
        lines.append(head_extra)
    lines.append("</head>")
    return "\n".join(lines).replace("\n  \n", "\n") + "\n"


# ── chrome ───────────────────────────────────────────────────────────────────

def topbar(*, labels: dict[str, str]) -> str:
    """Top bar widgets (showcase chrome). No DGA digital stamp, no brand switcher:
    the owner removed government identity, and the event/predefined theme packs are
    not hosted by this project. Date and clock are the documented topbar widgets.
    """
    return f"""<div class="nds-topbar nds-content-wrapper" role="region" aria-label="{labels['region']}">
      <div class="nds-topbar-info">
        <span id="nds-date" class="nds-text-icon" data-calendar="hijri" data-hidden="sm md"></span>
        <span id="nds-realTimeClock" class="nds-text-icon" data-hidden="sm"></span>
        <button class="nds-btn nds-subtle nds-icon-only nds-theme-toggle-wrap nds-tooltip" data-tooltip-hover="500" data-theme-toggle title="{labels['toggle_dark']}" aria-label="{labels['toggle_dark']}">
          <i class="nds-icon nds-hgi-moon-02" aria-hidden="true"></i>
        </button>
      </div>
    </div>"""


def mainnav(
    *,
    nav_id: str,
    aria_label: str,
    brand_href: str,
    brand_logo: str,
    brand_name: str,
    brand_slogan: str,
    toggle_label: str,
    primary: list[dict],
    actions: list[str],
) -> str:
    """ui-shell/mainnav.md → Navigation Bar, with the documented action patterns.

    `primary` items: {"href", "label"}. `actions` is pre-rendered markup so each
    page owns its own action set (language switch, theme toggle, showcase link).
    """
    items = "\n".join(
        f"""            <li class="nds-nav-item">
              <a href="{item['href']}" class="nds-nav-link nds-btn nds-subtle nds-indicator">
                <span class="nds-label">{item['label']}</span>
              </a>
            </li>"""
        for item in primary
    )
    return normalize(f"""<nav class="nds-main-nav nds-content-wrapper" id="{nav_id}" aria-label="{aria_label}">
      <div class="nds-nav-container">
        <a class="nds-brand" href="{brand_href}">
          <img class="nds-brand-logo" src="{brand_logo}" width="40" height="40" alt="">
          <span class="nds-brand-name">{brand_name}
            <span class="nds-brand-slogan">{brand_slogan}</span>
          </span>
        </a>
        <ul class="nds-nav-minimal" hidden>
          <li class="nds-mainNav-toggler nds-nav-item">
            <button type="button" class="nds-nav-link nds-btn nds-subtle nds-indicator" aria-label="{toggle_label}" aria-expanded="false" aria-controls="ndsNavCollapse">
              <i class="nds-icon nds-hgi-menu-01" aria-hidden="true"></i>
            </button>
          </li>
        </ul>
        <div class="nds-collapse" id="ndsNavCollapse" hidden>
          <div class="nds-collapse-content">
            <ul class="nds-nav-primary">
{items}
            </ul>
            <div class="nds-nav-item nds-show-more">
              <a class="nds-nav-link nds-btn nds-subtle nds-indicator nds-full">
                <i class="nds-icon nds-hgi-arrow-down-01" aria-hidden="true"></i>
              </a>
            </div>
            <ul class="nds-nav-actions">
{chr(10).join(actions)}
            </ul>
          </div>
        </div>
      </div>
    </nav>""")


def nav_action_item(inner: str, *, extra_class: str = "") -> str:
    classes = f"nds-nav-item nds-icon-only nds-PAB{(' ' + extra_class) if extra_class else ''}"
    return f'              <li class="{classes}">\n{inner}\n              </li>'


def footer(
    *,
    aria_label: str,
    nav_label: str,
    columns: list[dict],
    copyright_text: str,
    versions: str = "",
) -> str:
    """_includes/footer.html: contentinfo role, link columns, divider, bottom row."""
    rendered = []
    for index, column in enumerate(columns, start=1):
        links = "\n".join(
            f"""            <li>
              <a class="nds-link nds-footer-link{(' ' + link['class']) if link.get('class') else ''}" href="{link['href']}">
                {f'<i class="nds-icon {link["icon"]}" aria-hidden="true"></i>' if link.get('icon') else ''}
                <span class="nds-label">{link['label']}</span>
              </a>
            </li>"""
            for link in column["links"]
        )
        rendered.append(
            f"""        <div class="nds-footer-column">
          <span class="nds-footer-heading" id="nds-footer-col-{index}">{column['heading']}</span>
          <ul class="nds-footer-list" aria-labelledby="nds-footer-col-{index}">
{links}
          </ul>
        </div>"""
        )
    versions_html = (
        f"""          <div class="nds-footer-versions">
{versions}
          </div>"""
        if versions
        else ""
    )
    return normalize(f"""<footer class="nds-footer nds-content-wrapper nds-brand" role="contentinfo" aria-label="{aria_label}">
      <nav class="nds-footer-content" aria-label="{nav_label}">
{chr(10).join(rendered)}
      </nav>
      <hr class="nds-divider nds-lg">
      <div class="nds-footer-bottom">
        <div class="nds-footer-meta">
          <div class="nds-footer-legal">
            <div class="nds-footer-copyright">
              <span>{copyright_text}</span>
            </div>
{versions_html}
          </div>
        </div>
      </div>
    </footer>""")


def version_tags(*, label_prefix: str = "") -> str:
    """The footer version pills: the pinned NDS release and the installed IQ revision."""
    iq = PIN["nds_iq"]["installed_version"]
    return (
        f'            <span class="nds-tag nds-xs nds-oncolor">'
        f'<span class="nds-label">{label_prefix}NDS v{PIN["runtime_version_banner"]}</span></span>\n'
        f'            <span class="nds-tag nds-xs nds-oncolor">'
        f'<span class="nds-label">NDS IQ v{iq}</span></span>'
    )


def runtime_scripts(*, page_module: str | None = None) -> str:
    """_layouts/default.html script order: main bundle, accessibility add-on, page JS."""
    tags = [
        f'  <script defer src="{versioned("js/nds-main.min.js")}"></script>',
        f'  <script defer src="{versioned("js/nds-accessibility.min.js")}"></script>',
    ]
    if page_module:
        tags.append(f'  <script type="module" src="{page_module}"></script>')
    return "\n".join(tags)


def page_document(*, head: str, body_class: str, parts: list[str]) -> str:
    """_layouts/default.html body order: header, main, footer, panel, scripts."""
    body = [head.rstrip("\n"), f'<body class="{body_class}">']
    body += [part for part in parts if part]
    body += ["</body>", "</html>"]
    return "\n".join(body) + "\n"


def normalize(text: str) -> str:
    """Re-base a generated fragment at column 0 (the first line already is)."""
    lines = text.splitlines()
    indents = [len(line) - len(line.lstrip()) for line in lines[1:] if line.strip()]
    shift = min(indents) if indents else 0
    if not shift:
        return text
    return "\n".join([lines[0]] + [line[shift:] if line.strip() else line for line in lines[1:]])


def indent(text: str, spaces: int) -> str:
    """Indent a generated fragment so the published page stays readable."""
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def tidy(text: str) -> str:
    """Trim trailing whitespace per line, as the project's other generated files."""
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


# ── CSP ──────────────────────────────────────────────────────────────────────

def generated_html() -> list[pathlib.Path]:
    """Every page the generators publish, so the CSP covers the site and the showcase."""
    found = [path for path in (ROOT / "index.html", ROOT / "404.html") if path.is_file()]
    found += sorted((ROOT / "en").glob("*.html")) if (ROOT / "en").is_dir() else []
    found += sorted((ROOT / "nds-showcase").rglob("*.html")) if (ROOT / "nds-showcase").is_dir() else []
    return found


def write_csp_for_tree() -> tuple[str, int]:
    pages = generated_html()
    return write_csp([path.read_text(encoding="utf-8") for path in pages]), len(pages)


def write_csp(pages: list[str]) -> str:
    """Refresh the CSP hash lists for every generated page.

    ui-shell/head.md §CSP: a static host authorises inline script/style by hash.
    The policy keeps `style-src-attr 'unsafe-inline'` because NDS components write
    their own style attributes at runtime; authored HTML carries none.
    """
    import base64
    import hashlib

    def hashes(tag: str) -> str:
        bodies = {
            match.group(1)
            for page in pages
            for match in re.finditer(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", page, re.S)
            if match.group(1).strip()
        }
        return " ".join(
            "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
            for body in sorted(bodies)
        )

    policy = (
        "default-src 'self'; img-src 'self' data:; font-src 'self'; "
        "style-src 'self' " + hashes("style") + "; style-src-attr 'unsafe-inline'; "
        "script-src 'self' " + hashes("script") + "; script-src-attr 'none'; "
        "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )

    headers_path = ROOT / "_headers"
    headers = headers_path.read_text(encoding="utf-8")
    headers, count = re.subn(
        r"(?m)^  Content-Security-Policy:.*$", "  Content-Security-Policy: " + policy, headers
    )
    if count != 1:
        raise SystemExit("Expected exactly one CSP header in _headers")
    headers_path.write_text(headers, encoding="utf-8")

    # Vercel remains an optional static host with an identical security policy.
    vercel_path = ROOT / "vercel.json"
    vercel = json.loads(vercel_path.read_text(encoding="utf-8"))
    for rule in vercel["headers"]:
        for header in rule["headers"]:
            if header["key"] == "Content-Security-Policy":
                header["value"] = policy
    vercel_path.write_text(json.dumps(vercel, indent=2) + "\n", encoding="utf-8")
    return policy
