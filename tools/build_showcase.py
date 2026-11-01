#!/usr/bin/env python3
"""Generates the NDS component showcase under /nds-showcase/.

  python3 tools/build.py        (builds the site and the showcase, then the CSP)

Every entry of the pinned release's official catalog
(`.nds/_source/_data/content/components.yml`, 98 entries / 9 categories) gets a
page built from that entry's own documentation file, so nothing can silently
disappear: the coverage checklist in docs/NDS-SHOWCASE.md is generated from the
same catalog and records the outcome per entry.

Examples are the documentation's own canonical markup — the contents of its
`<code class="lang-html code">` blocks — rendered live and repeated in a
canonical `.nds-code` block. No screenshot, no re-implementation, no docs-site
demo chrome (`.nds-showcase`, `.demo-*`, `nds-showcase.min.css/js`, `data-toggler`
are never copied).

Page templates and examples (`templates/*.md`, `examples/*.md`) are rendered as
full pages through the same `_layouts/page.html` structure. Their bodies are
Jekyll/Liquid; a bounded resolver handles the constructs they actually use and
leaves an HTML comment plus a `partial` checklist flag for anything else, so a
page is never silently wrong.

Generated: nds-showcase/index.html, nds-showcase/<dir>/<name>.html,
           docs/NDS-SHOWCASE.md
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import nds_shell  # noqa: E402
from nds_shell import asset, versioned  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".nds" / "_source"
OUT = ROOT / "nds-showcase"
PIN = json.loads((ROOT / "tools" / "nds-pin.json").read_text(encoding="utf-8"))
VERSION = PIN["runtime_version_banner"]

# Images the pinned tag keeps out of this project (government identity in
# assets/img/, documentation imagery in docs-assets/). A demo that asks for one
# gets a labelled local placeholder instead of a broken image or a copied seal.
PLACEHOLDER = asset("img/showcase-placeholder.svg")
ASSET_DIRS = ("assets/",)

# ── minimal YAML subset ──────────────────────────────────────────────────────
# The project builds with the standard library only. The catalog and the demo
# data files are flat lists of mappings with scalar, boolean and inline-list
# values; anything else raises instead of being guessed at.

SCALAR = re.compile(r'^([A-Za-z_][\w-]*):\s*(.*)$')


def yaml_list(text: str) -> list[dict]:
    """Parse the flat list-of-mappings shape the NDS catalog and demo data use.

    Supports scalars (quoted, bare, boolean, number), inline lists, block lists
    one level deep, and multi-line quoted scalars — which is all of
    `_data/content/*.yml` in the pinned tag. Anything else raises.
    """
    items: list[dict] = []
    current: dict | None = None
    last_key: str | None = None
    pending: tuple[str, str, list[str]] | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if pending:
            key, quote, buffer = pending
            buffer.append(stripped)
            if stripped.endswith(quote):
                current[key] = " ".join(buffer)[:-1]
                pending = None
            continue

        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith("- "):
            current = {}
            items.append(current)
            last_key = None
            stripped = line[2:].strip()
            if not stripped:
                continue
        elif line.startswith("  - ") or line.startswith("    - "):
            if current is None or last_key is None:
                raise SystemExit(f"block list item without a key: {raw!r}")
            if not isinstance(current.get(last_key), list):
                current[last_key] = []
            current[last_key].append(yaml_scalar(stripped[2:]))
            continue

        if current is None:
            raise SystemExit(f"YAML line outside a list item: {raw!r}")

        match = SCALAR.match(stripped)
        if not match:
            raise SystemExit(f"unsupported YAML shape: {raw!r}")
        key, value = match.group(1), match.group(2).strip()
        last_key = key
        if value and value[0] in "\"'" and not (len(value) > 1 and value[-1] == value[0]):
            pending = (key, value[0], [value[1:]])
            continue
        current[key] = yaml_scalar(value) if value else []

    if pending:
        raise SystemExit("unterminated multi-line scalar in the NDS catalog")
    return items


def yaml_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [yaml_scalar(part) for part in split_inline(inner)] if inner else []
    if value.startswith("{") and value.endswith("}"):
        # Flow mapping, e.g. `{ label: Overview, color: blue }` (faqs.yml tags).
        inner = value[1:-1].strip()
        mapping = {}
        for part in split_inline(inner):
            key, _, item_value = part.partition(":")
            mapping[key.strip()] = yaml_scalar(item_value)
        return mapping
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+(\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def split_inline(text: str) -> list[str]:
    parts, depth, quote, current = [], 0, "", ""
    for ch in text:
        if quote:
            current += ch
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            current += ch
        elif ch in "[{":
            depth += 1
            current += ch
        elif ch in "]}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


# ── documentation parsing ────────────────────────────────────────────────────

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
HTML_BLOCK = re.compile(r'<code class="lang-html code">(.*?)</code>', re.S)
JS_BLOCK = re.compile(r'<code class="lang-(?:javascript|json|liquid|scss|css)[^"]*">(.*?)</code>', re.S)
SECTION_OPEN = re.compile(r'<section\b[^>]*>')


def front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER.match(text)
    if not match:
        return {}, text
    data = {}
    key = None
    for line in match.group(1).splitlines():
        if re.match(r"^\s*#", line) or not line.strip():
            continue
        if re.match(r"^-\s", line) and key:
            value = line.split("-", 1)[1].strip()
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(yaml_scalar(value))
            continue
        match2 = SCALAR.match(line)
        if match2:
            key, value = match2.group(1), match2.group(2).strip()
            data[key] = yaml_scalar(value) if value else []
    return data, text[match.end():]


def split_sections(body: str) -> list[dict]:
    """Top-level `<section>` blocks of a documentation page, in order."""
    sections, depth, start, cursor = [], 0, None, 0
    for match in re.finditer(r"<section\b[^>]*>|</section>", body):
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0 and start is not None:
                sections.append({"raw": body[start:match.end()], "index": cursor})
                cursor += 1
                start = None
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    parsed = []
    for section in sections:
        raw = section["raw"]
        id_match = re.search(r'\bid="([^"]+)"', raw)
        title = first_text(raw, r'<h2 class="nds-section-title">(.*?)</h2>')
        description = first_text(raw, r'<p class="nds-section-description">(.*?)</p>')
        parsed.append({
            "id": id_match.group(1) if id_match else f"section-{section['index'] + 1}",
            "title": title or f"Section {section['index'] + 1}",
            "description": description,
            "html": [html.unescape(m.group(1)).strip() for m in HTML_BLOCK.finditer(raw)],
            "js": [html.unescape(m.group(1)).strip() for m in JS_BLOCK.finditer(raw)],
            "tables": re.findall(r"<table\b.*?</table>", raw, re.S),
            "raw": raw,
        })
    return parsed


def first_text(raw: str, pattern: str) -> str:
    match = re.search(pattern, raw, re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", strip_tags(match.group(1))).strip()


def strip_tags(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


# ── demo markup preparation ──────────────────────────────────────────────────

ID_ATTRS = (
    "id", "for", "list", "aria-controls", "aria-labelledby", "aria-describedby",
    "aria-owns", "data-target", "data-panel-toggle", "data-modal", "data-drawer",
    "data-accordion", "data-tabs", "data-toggler", "data-popover", "data-tooltip-target",
    "data-multiselect", "data-autocomplete", "data-form", "data-menu", "data-dropdown",
)


def uniquify(markup: str, suffix: str) -> str:
    """Give one demo instance its own IDs so sibling demos cannot cross-wire.

    NDS binds by id (`data-panel-toggle`, `data-modal`, `for`, `aria-controls`,
    `#fragment` links). Rendering the same canonical block twice on a page needs
    both instances renamed consistently or the second one controls the first.
    """
    ids = set(re.findall(r'\bid="([^"]+)"', markup))
    if not ids:
        return markup

    def attribute(match: re.Match) -> str:
        name, value = match.group(1), match.group(2)
        if name == "id":
            return f'id="{value}{suffix}"' if value in ids else match.group(0)
        if value.startswith("#"):
            fragment = value[1:]
            return f'{name}="#{fragment}{suffix}"' if fragment in ids else match.group(0)
        tokens = value.split()
        if tokens and any(token in ids for token in tokens):
            return f'{name}="{" ".join(t + suffix if t in ids else t for t in tokens)}"'
        return match.group(0)

    markup = re.sub(r"\b(" + "|".join(ID_ATTRS) + r')="([^"]*)"', attribute, markup)
    # Any other attribute holding a #fragment that points at one of our ids.
    markup = re.sub(
        r'\b(data-[\w-]+)="#([\w:-]+)"',
        lambda m: f'{m.group(1)}="#{m.group(2)}{suffix}"' if m.group(2) in ids else m.group(0),
        markup,
    )
    markup = re.sub(
        r'\b(href|src)="#([\w:-]+)"',
        lambda m: f'{m.group(1)}="#{m.group(2)}{suffix}"' if m.group(2) in ids else m.group(0),
        markup,
    )
    # Form controls sharing a name across demos would share selection state.
    markup = re.sub(
        r'(<(?:input|select|textarea)\b[^>]*?\bname=")([^"]+)(")',
        lambda m: m.group(1) + m.group(2) + suffix + m.group(3),
        markup,
    )
    return markup


def docs_only_hooks(markup: str, runtime_hooks: set[str]) -> list[str]:
    """data-* attributes in an example that the NDS runtime never reads.

    The documentation's own demo script (docs-only `nds-showcase.min.js`, which
    this project does not ship) drives those, so the interaction is inert here and
    the page says so instead of pretending it works.
    """
    found = []
    for match in re.finditer(r"\b(data-[a-z0-9-]+)=", markup):
        hook = match.group(1)
        if hook not in runtime_hooks and hook not in found:
            found.append(hook)
    return found


DOCS_ORIGIN = "https://mazin-musleh.github.io/NDS-vanilla"
DOC_LINK = re.compile(r"\{\{\s*'([^']+)'\s*\|\s*relative_url\s*\}\}")
# Upstream's own language routes, quoted inside its examples. This site serves
# Arabic at / and English at /en/ (NDS IQ edit class #1: rewrite the URL only).
UPSTREAM_ROUTES = {'href="/ar/"': 'href="/"', 'href="/ar"': 'href="/"',
                   'href="/en/"': 'href="/en/"', 'href="/en"': 'href="/en/"'}


PLANNED_PAGES: set[str] = set()


def plan_pages() -> set[str]:
    """Every route this run publishes, computed from the pinned catalog.

    Doc links inside quoted examples resolve against this set, so a clean checkout
    links to the showcase pages that are about to be written instead of depending
    on a previous build being present.
    """
    planned = {"/nds-showcase/", "/nds-showcase/index.html", "/nds-showcase/templates/", "/nds-showcase/examples/"}
    catalog = yaml_list((SOURCE / "_data" / "content" / "components.yml").read_text(encoding="utf-8"))
    for entry in catalog:
        base = entry["url"].split("#", 1)[0].strip("/")
        planned.add(f"/nds-showcase/{base}")
    for kind in ("templates", "examples"):
        for source in sorted((SOURCE / kind).glob("*.md")):
            if source.name == "index.md":
                continue
            planned.add(f"/nds-showcase/{kind}/{source.stem}.html")
    PLANNED_PAGES.clear()
    PLANNED_PAGES.update(planned)
    return PLANNED_PAGES


def generated_pages() -> set[str]:
    """Relative paths this showcase publishes, so doc links can point at them."""
    return PLANNED_PAGES or plan_pages()


def resolve_doc_links(markup: str) -> str:
    """Rewrite documentation URLs inside quoted examples (NDS IQ edit class #1).

    `{{ 'components/fab' | relative_url }}` is the docs site's own link syntax. It
    becomes this showcase's page when the entry is generated here, a project asset
    when the file exists, and the official documentation page otherwise — never a
    dead local link.
    """

    def rewrite(match: re.Match) -> str:
        target = match.group(1).strip("/")
        for candidate in (f"/nds-showcase/{target}.html", f"/nds-showcase/{target}/"):
            if candidate in generated_pages():
                return candidate
        if (ROOT / target).is_file():
            return "/" + target
        return f"{DOCS_ORIGIN}/{target}.html"

    for source, target in UPSTREAM_ROUTES.items():
        markup = markup.replace(source, target)
    return DOC_LINK.sub(rewrite, markup)


PLACEHOLDER_ROUTE = re.compile(r'\b(href|action)="(/[\w./-]*)"')


def quoted_placeholder_routes(markup: str) -> list[str]:
    """Root-relative targets inside an example that this project does not serve.

    They are the documentation's own placeholders (`/user/profile`,
    `/privacy-policy`, `/services/…`). Quoted as published and reported on the page
    rather than rewritten into something that looks like it works.
    """
    published = generated_pages()
    found = []
    for match in PLACEHOLDER_ROUTE.finditer(markup):
        target = match.group(2)
        if target in ("/", "/en/", "/nds-showcase/") or target in published:
            continue
        if (ROOT / target.lstrip("/")).exists():
            continue
        if target.startswith("/assets/"):
            continue
        if target not in found:
            found.append(target)
    return found


def strip_scripts(markup: str) -> tuple[str, int]:
    """CSP forbids inline scripts; a demo's init sample is shown as code instead."""
    scripts = re.findall(r"<script\b.*?</script>", markup, re.S | re.I)
    return re.sub(r"<script\b.*?</script>", "", markup, flags=re.S | re.I).strip(), len(scripts)


def localise_assets(markup: str, missing: set[str]) -> str:
    """Point demo asset URLs at this project; unavailable ones get a placeholder."""

    def rewrite(match: re.Match) -> str:
        attr, value = match.group(1), match.group(2)
        if value.startswith(("http://", "https://", "data:", "#", "mailto:", "tel:", "/")):
            return match.group(0)
        candidate = ROOT / value
        if candidate.is_file():
            return f'{attr}="/{value}"'
        missing.add(value)
        return f'{attr}="{PLACEHOLDER}"'

    return re.sub(r'\b(src|href|poster)="([^"]+\.(?:png|jpe?g|webp|svg|gif|avif|woff2?))"', rewrite, markup)


# ── Liquid subset (templates and examples only) ──────────────────────────────
# tools/liquid_subset.py renders the pinned release's Jekyll sources with exactly
# the constructs they use; anything else is reported so the row is flagged
# `partial` in docs/NDS-SHOWCASE.md instead of being silently approximated.

from liquid_subset import Renderer  # noqa: E402
from check_nds_usage import runtime_hooks  # noqa: E402

RUNTIME_HOOKS = None


def hooks_read_by_runtime() -> set[str]:
    global RUNTIME_HOOKS
    if RUNTIME_HOOKS is None:
        RUNTIME_HOOKS = runtime_hooks()
    return RUNTIME_HOOKS


def render_source(body: str, matter: dict) -> tuple[str, list[str]]:
    renderer = Renderer(SOURCE / "_data" / "content", ROOT, PLACEHOLDER)
    page = dict(matter)
    page.setdefault("lang", "en")
    page.setdefault("direction", "ltr")
    rendered = renderer.render(body, page=page)
    return rendered, renderer.unresolved


def partial_note(unresolved: list[str], removed_scripts: int, missing_assets: set[str]) -> str:
    """Honest labelling of what this generated page could not reproduce."""
    items = []
    if unresolved:
        unique = sorted(set(unresolved))
        items.append(
            f"{len(unresolved)} Liquid node(s) outside the generator's bounded subset "
            f"({', '.join(unique[:4])}{'…' if len(unique) > 4 else ''}) are left as HTML "
            "comments in the markup"
        )
    if removed_scripts:
        items.append(f"{removed_scripts} inline script sample(s) shown as code only (CSP forbids inline scripts)")
    if missing_assets:
        unique = sorted(missing_assets)
        items.append(
            f"{len(missing_assets)} documentation asset(s) replaced by a labelled placeholder "
            f"({', '.join(unique[:3])}{'…' if len(unique) > 3 else ''})"
        )
    if not items:
        return ""
    lis = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"""        <section id="generator-notes" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-body">
              <div class="nds-alert nds-card nds-color" data-status="warning" role="note">
                <span class="nds-feedback nds-alert-icon nds-outline">
                  <span class="nds-feedback-icon"><i class="nds-icon" aria-hidden="true"></i></span>
                </span>
                <div class="nds-alert-content">
                  <div class="nds-alert-text">
                    <span class="nds-alert-title">Generated from the pinned release's Jekyll source</span>
                    <ul class="nds-alert-description">{lis}</ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
"""


# ── page chrome ──────────────────────────────────────────────────────────────

SHOWCASE_HOME = "/nds-showcase/"


def chrome_head(title: str, description: str, *, path: str) -> str:
    # document_head() takes pre-escaped head strings (the same contract build.py
    # uses). Catalog descriptions quote other page names, so the double quotes
    # have to be escaped before they reach the meta attribute.
    return nds_shell.document_head(
        lang="en",
        direction="ltr",
        title=html.escape(f"{title} · NDS {VERSION} showcase"),
        description=html.escape(description),
        extra_meta="\n  ".join([
            '<meta name="robots" content="noindex, nofollow">',
            '<meta name="theme-color" content="#0e5a49">',
        ]),
        head_extra="    " + NOJS_CSS.replace("\n", "\n    "),
    )


NOJS_CSS = """<noscript>
      <style>.alq-site :is(.nds-sideinfo, .nds-toc, .nds-drawer),
      .alq-site :is(.nds-sideinfo, .nds-toc, .nds-drawer) > *,
      .alq-site .nds-main-nav > *,
      .alq-site .nds-code .nds-expandable-content { visibility: visible; }</style>
    </noscript>"""


def chrome_nav(active: str, breadcrumb_label: str) -> str:
    primary = [
        {"href": SHOWCASE_HOME, "label": "Index"},
        {"href": "/", "label": "Arabic site"},
        {"href": "/en/", "label": "English site"},
    ]
    actions = [
        nds_shell.nav_action_item(
            """                <a href="/" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-tooltip" data-tooltip-hover="500" title="Back to the personal site" lang="ar" hreflang="ar">
                  <i class="nds-icon nds-hgi-arrow-left-01" aria-hidden="true"></i>
                  <span class="nds-label" data-hidden="sm md sr">Personal site</span>
                </a>"""
        ),
        nds_shell.nav_action_item(
            """                <button type="button" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-theme-toggle-wrap nds-tooltip" data-tooltip-hover="500" data-theme-toggle title="Toggle dark mode" aria-label="Toggle dark mode" aria-pressed="false">
                  <i class="nds-icon nds-hgi-moon-02" aria-hidden="true"></i>
                </button>"""
        ),
    ]
    nav = nds_shell.mainnav(
        nav_id="ndsMainNav",
        aria_label="Primary navigation",
        brand_href=SHOWCASE_HOME,
        brand_logo=asset("img/favicon.svg"),
        brand_name=f"NDS {VERSION}",
        brand_slogan="Component showcase",
        toggle_label="Toggle navigation menu",
        primary=primary,
        actions=actions,
    )
    prelude = """  <a class="alq-skip-link" href="#main-content">Skip to content</a>
  <noscript>
    <nav class="alq-fallback" aria-label="Navigation without JavaScript">
      <a href="/nds-showcase/">Showcase index</a>
      <a href="/">Arabic site</a>
      <a href="/en/">English site</a>
    </nav>
  </noscript>"""
    return prelude + "\n  <header>\n" + nds_shell.indent(nav, 4) + "\n  </header>"


def chrome_footer() -> str:
    return nds_shell.footer(
        aria_label="Site Footer",
        nav_label="Footer navigation",
        columns=[
            {
                "heading": "Showcase",
                "links": [
                    {"href": SHOWCASE_HOME, "label": "Component index"},
                    {"href": "/nds-showcase/templates/", "label": "Page templates"},
                    {"href": "/nds-showcase/examples/", "label": "Full examples"},
                ],
            },
            {
                "heading": "Personal site",
                "links": [
                    {"href": "/", "label": "Arabic (RTL)", "icon": "nds-hgi-arrow-left-01"},
                    {"href": "/en/", "label": "English (LTR)", "icon": "nds-hgi-arrow-right-01"},
                ],
            },
        ],
        copyright_text=(
            f"Component examples are quoted from NDS v{VERSION} "
            f"(commit {PIN['commit'][:12]}, MIT). This is a personal review route, "
            "not a government service."
        ),
        versions=nds_shell.version_tags(),
    )


def hero_sub(*, title: str, description: str, crumbs: list[tuple[str, str]], style: str = "nds-flat") -> str:
    """ui-shell/hero.md sub hero; crumbs are (label, href) with href '' for text."""
    items = "\n".join(
        f'            <li><a href="{href}">{html.escape(label)}</a></li>' if href
        else f'            <li class="nds-truncate" aria-current="page">{html.escape(label)}</li>'
        for label, href in crumbs
    )
    return f"""  <main>
    <section class="nds-hero-section nds-sub {style}" id="top">
      <nav class="nds-breadcrumb-nav" aria-label="Breadcrumb">
        <ol class="nds-breadcrumb">
{items}
        </ol>
      </nav>
      <div class="nds-section-wrapper">
        <div class="nds-section-head">
          <h1 class="nds-section-title">{html.escape(title)}</h1>
          <p class="nds-section-description">{html.escape(description)}</p>
        </div>
      </div>
    </section>"""


DOCUMENT_NODES = re.compile(r"<\s*(?:html|head|body|title|meta|link|style)\b", re.I)
UNRESOLVED_LIQUID = re.compile(r"\{\{|\{%")


def cannot_instantiate(prepared: str) -> str:
    """Why a documented example is quoted as source instead of rendered live.

    Two cases genuinely cannot exist inside a generated showcase page:

    * Liquid templates. The documentation site resolves loops and variables with
      Jekyll; this showcase is a static build with no Liquid runtime, so an
      unresolved template would ship invalid markup such as ``id="x-{{ item.id }}"``.
    * Document-level nodes (``<html>``, ``<head>``, ``<meta>``, ``<link>``, ``<style>``).
      The examples document attributes that belong on the document root or head, and
      HTML forbids nesting them in a body.

    Both are shown verbatim in the example's code block, which is the honest way to
    publish them; nothing is silently dropped.
    """
    if UNRESOLVED_LIQUID.search(prepared):
        return (
            "Source only: this example is a Liquid template. Its loops and variables are "
            "resolved by the documentation site's Jekyll build, which this static showcase "
            "does not run, so the markup is quoted exactly as published rather than rendered."
        )
    match = DOCUMENT_NODES.search(prepared)
    if match:
        node = match.group(0).lstrip("<").strip().lower()
        return (
            f"Source only: this example documents a <{node}> node, which belongs on the "
            "document root or head and cannot be nested inside this page's body. The markup "
            "is quoted exactly as published."
        )
    return ""


GOVERNMENT_IDENTITY = re.compile(
    r"nds-digitalStamp|Digital Government Authority|government\s+website|nds-flag\b", re.I
)


def identity_block(index: int, source_path: str) -> str:
    """Replace a documented example that carries a government identity.

    The release documents a national registration stamp (a flag, a seal and the
    sentence that registers the page as an official government website). This is
    a personal website, so that markup is neither rendered nor quoted: publishing
    even its text would present a government identity the site does not have. The
    omission is recorded here, on the page, and in the coverage checklist.
    """
    origin = html.escape(source_path or "the pinned release")
    return f"""          <div class="nds-block">
            <div class="nds-card nds-stroke alq-full">
              <div class="nds-card-content">
                <span class="nds-card-title">Example {index}</span>
                <p class="nds-card-description">Excluded from this site: the documented
                example is a national government registration stamp (flag, seal and the
                wording that presents a page as an official government website). This is a
                personal website, so neither the markup nor its wording is reproduced here.
                The authoritative source is <code class="nds-inline-code">{origin}</code>
                inside the pinned tag.</p>
              </div>
            </div>
          </div>"""


def demo_block(markup: str, index: int, *, missing: set[str], note: str = "",
               source_path: str = "") -> tuple[str, int]:
    """One live example plus its canonical code block. Returns (html, removed_scripts)."""
    if GOVERNMENT_IDENTITY.search(markup):
        return identity_block(index, source_path), 0
    suffix = f"-ex{index}"
    prepared, removed = strip_scripts(markup)
    prepared = resolve_doc_links(prepared)
    placeholders = quoted_placeholder_routes(prepared)
    prepared = localise_assets(prepared, missing)
    prepared = uniquify(prepared, suffix)
    code_id = f"code{suffix}"
    if placeholders:
        note = (note + " " if note else "") + (
            "Link note: "
            + ", ".join(placeholders[:4])
            + ("…" if len(placeholders) > 4 else "")
            + " are placeholder routes from the documentation, quoted as published; "
            "this personal site serves no such pages."
        )
    inert = docs_only_hooks(markup, hooks_read_by_runtime())
    if inert:
        note = (note + " " if note else "") + (
            "Interaction note: this example carries page-local data attributes ("
            + ", ".join(inert)
            + ") that the NDS documentation site's own demo script wires. That docs-only "
            "script is not shipped here, so this specific interaction is inert; the markup "
            "and the NDS runtime behaviour around it are canonical."
        )
    source_reason = cannot_instantiate(prepared)
    if source_reason:
        note = (note + " " if note else "") + source_reason
    note_html = (
        f'            <p class="nds-card-description">{html.escape(note)}</p>\n' if note else ""
    )
    script_note = (
        '            <p class="nds-card-description">The documentation\'s inline <code class="nds-inline-code">script</code> '
        "sample is not executed here (this site's CSP forbids inline scripts); it is shown as code below.</p>\n"
        if removed
        else ""
    )
    live = (
        f"""                <div class="nds-card-text">
{nds_shell.indent(prepared, 18)}
                </div>"""
        if not source_reason
        else ""
    )
    return f"""          <div class="nds-block">
            <div class="nds-card nds-stroke alq-full">
              <div class="nds-card-content">
                <span class="nds-card-title">Example {index}</span>
{note_html}{script_note}{live}
              </div>
            </div>
            <div class="nds-code nds-expandable">
              <div class="nds-code-action">
                <button class="nds-btn nds-subtle nds-copy" type="button" aria-label="Copy code example" aria-controls="{code_id}">
                  <i class="nds-icon nds-hgi-copy-01" aria-hidden="true"></i>
                </button>
              </div>
              <div class="nds-expandable-content">
                <code class="lang-html code" id="{code_id}">{html.escape(markup)}</code>
              </div>
            </div>
          </div>""", removed


def prose_source(markup: str, index: int, note: str) -> str:
    """A documentation block quoted verbatim as source instead of live markup."""
    code_id = f"src-{index}"
    return f"""          <div class="nds-block">
            <div class="nds-card nds-stroke alq-full">
              <div class="nds-card-content">
                <span class="nds-card-title">Source {index}</span>
                <p class="nds-card-description">{html.escape(note)}</p>
              </div>
            </div>
            <div class="nds-code nds-expandable">
              <div class="nds-code-action">
                <button class="nds-btn nds-subtle nds-copy" type="button" aria-label="Copy source example" aria-controls="{code_id}">
                  <i class="nds-icon nds-hgi-copy-01" aria-hidden="true"></i>
                </button>
              </div>
              <div class="nds-expandable-content">
                <code class="lang-html code" id="{code_id}">{html.escape(markup)}</code>
              </div>
            </div>
          </div>"""


def code_only(sample: str, index: int, language: str = "javascript") -> str:
    code_id = f"api-{index}"
    return f"""          <div class="nds-block">
            <div class="nds-code nds-expandable">
              <div class="nds-code-action">
                <button class="nds-btn nds-subtle nds-copy" type="button" aria-label="Copy code example" aria-controls="{code_id}">
                  <i class="nds-icon nds-hgi-copy-01" aria-hidden="true"></i>
                </button>
              </div>
              <div class="nds-expandable-content">
                <code class="lang-{language}" id="{code_id}">{html.escape(sample)}</code>
              </div>
            </div>
          </div>"""


def doc_page(*, title: str, description: str, crumbs: list[tuple[str, str]], sections: list[dict],
             path: str, source_path: str, entry: dict | None = None,
             panel: bool = False, skip: dict[str, str] | None = None) -> tuple[str, dict]:
    """A showcase page whose body is the documentation's own canonical examples."""
    missing: set[str] = set()
    stats = {"examples": 0, "api_samples": 0, "sections": 0, "partial": False, "rendered_ids": [],
             "skipped": {}, "identity_excluded": 0}
    rendered = []
    counter = 0
    toc = []
    for section in sections:
        if skip and section["id"] in skip:
            stats["skipped"][section["id"]] = skip[section["id"]]
            continue
        blocks = []
        for markup in section["html"]:
            counter += 1
            block, removed = demo_block(markup, counter, missing=missing, source_path=source_path)
            blocks.append(block)
            if GOVERNMENT_IDENTITY.search(markup):
                stats["identity_excluded"] += 1
                continue
            stats["examples"] += 1
        for sample in section["js"]:
            counter += 1
            blocks.append(code_only(sample, counter))
            stats["api_samples"] += 1
        for table in section["tables"]:
            # Reference tables quote the docs' own cross-links; rewritten like any
            # other asset/page URL so nothing points at a route this site lacks.
            quoted = resolve_doc_links(table.strip())
            if GOVERNMENT_IDENTITY.search(quoted):
                counter += 1
                blocks.append(identity_block(counter, source_path))
                stats["identity_excluded"] += 1
                continue
            reason = cannot_instantiate(quoted)
            if reason:
                # Some documentation "tables" are whole Liquid page skeletons. They
                # are published as source, not injected as live markup.
                counter += 1
                blocks.append(prose_source(quoted, counter, reason))
                stats["api_samples"] += 1
                continue
            blocks.append(
                '          <div class="nds-block nds-prose">\n'
                + nds_shell.indent(quoted, 12)
                + "\n          </div>"
            )
        if not blocks:
            continue
        stats["sections"] += 1
        stats["rendered_ids"].append(section["id"])
        anchor = section["id"]
        toc.append((anchor, section["title"]))
        head = f"""          <div class="nds-section-head">
            <h2 class="nds-section-title">{html.escape(section['title'])}</h2>"""
        if section["description"]:
            head += f'\n            <p class="nds-section-description">{html.escape(section["description"])}</p>'
        head += "\n          </div>"
        rendered.append(
            f"""        <section id="{anchor}" class="nds-content-section">
          <div class="nds-section-wrapper">
{head}
            <div class="nds-section-body">
{chr(10).join(blocks)}
            </div>
          </div>
        </section>"""
        )

    if not rendered:
        stats["partial"] = True
        rendered.append(f"""        <section id="source" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-head">
              <h2 class="nds-section-title">Documented without renderable markup</h2>
              <p class="nds-section-description">This catalog entry is a container or API
              page: the pinned release documents it without a canonical HTML example of its
              own. The authoritative source is
              <code class="nds-inline-code">{html.escape(source_path)}</code> inside the pinned tag.</p>
            </div>
          </div>
        </section>""")

    tags = ""
    if entry:
        rendered_tags = "".join(
            f'            <span class="nds-tag nds-gray nds-sm"><span class="nds-label">{html.escape(str(tag))}</span></span>\n'
            for tag in (entry.get("tags") or [])
        )
        if rendered_tags:
            tags = f'          <div class="nds-flex nds-wrap alq-tags">\n{rendered_tags.rstrip()}\n          </div>\n'

    if stats["identity_excluded"]:
        rendered.insert(0, f"""        <section id="excluded-identity" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-body">
              <div class="nds-alert nds-card nds-color" data-status="info" role="note">
                <span class="nds-feedback nds-alert-icon nds-outline">
                  <span class="nds-feedback-icon"><i class="nds-icon" aria-hidden="true"></i></span>
                </span>
                <div class="nds-alert-content">
                  <div class="nds-alert-text">
                    <span class="nds-alert-title">{stats["identity_excluded"]} documented example(s) excluded on purpose</span>
                    <p class="nds-alert-description">They render a national government registration
                    stamp. This is a personal website and must not present a government identity, so
                    those examples are named in the coverage checklist but not reproduced.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>""")
        toc.insert(0, ("excluded-identity", "Excluded examples"))
    body = hero_sub(title=title, description=description, crumbs=crumbs) + "\n" + content_layout(
        rendered, toc, extra_head=tags
    )
    parts = [
        chrome_nav(path, title),
        body,
        nds_shell.indent(chrome_footer(), 2),
    ]
    if panel:
        parts.append(nds_shell.indent(nds_shell.accessibility_panel("en"), 2))
    parts.append(nds_shell.runtime_scripts(page_module=asset("js/site.js")))
    document = nds_shell.page_document(
        head=chrome_head(title, description, path=path), body_class="alq-site", parts=parts
    )
    stats["missing_assets"] = sorted(missing)
    return document, stats


def content_layout(sections: list[str], toc: list[tuple[str, str]], *, extra_head: str = "") -> str:
    """layout/page-shell.md: nds-wSideInfo with a canonical manual TOC."""
    links = "\n".join(
        f"""                <li>
                  <a href="#{anchor}" class="nds-btn nds-subtle nds-indicator">
                    <span class="nds-label nds-truncate">{html.escape(label)}</span>
                  </a>
                </li>"""
        for anchor, label in toc
    )
    sideinfo = ""
    if toc:
        sideinfo = f"""        <aside class="nds-sideinfo nds-md nds-sticky nds-top" aria-label="On this page">
          <nav class="nds-toc alq-toc" aria-label="Page section index">
            <div class="nds-toc-head">
              <span class="nds-label">On this page</span>
              <h2 class="nds-toc-title nds-truncate">Sections</h2>
            </div>
            <div class="nds-drawer nds-lined">
              <ul class="nds-drawer-list">
{links}
              </ul>
            </div>
          </nav>
        </aside>
"""
    return f"""    <div class="nds-content-layout nds-wSideInfo">
      <div class="nds-main-content" id="main-content">
        <section class="nds-content-section nds-sideinfo-section">
          <div class="nds-section-body">
{sideinfo}            <div class="nds-info-content">
{extra_head}{chr(10).join(sections)}
            </div>
          </div>
        </section>
      </div>
    </div>
  </main>"""


# ── catalog pages ────────────────────────────────────────────────────────────

# Catalog entries this personal site must not render: the DGA digital stamp is
# government identity (owner requirement), not a component gap. The entry stays in
# the checklist with its reason and the canonical source path.
SKIP_SECTIONS = {
    "ui-shell/topbar.md": {
        "dgaDigitalStamp": "government identity (DGA digital stamp, national flag, registration number): deliberately not rendered on a personal site",
    },
}


def doc_file_for(url: str) -> pathlib.Path | None:
    relative = url.split("#", 1)[0].strip("/").replace(".html", ".md")
    candidate = SOURCE / relative
    return candidate if candidate.is_file() else None


def build_catalog_pages(checklist: list[dict]) -> dict[pathlib.Path, str]:
    """One page per documentation file; catalog entries link to it (with anchors)."""
    pages: dict[pathlib.Path, str] = {}
    catalog = yaml_list((SOURCE / "_data" / "content" / "components.yml").read_text(encoding="utf-8"))
    by_doc: dict[str, list[tuple[dict, str]]] = {}
    for entry in catalog:
        base, _, fragment = entry["url"].partition("#")
        by_doc.setdefault(base, []).append((entry, fragment))

    for base, entries in by_doc.items():
        source = doc_file_for(base)
        relative = base.strip("/").replace(".html", "")
        out_path = OUT / f"{relative}.html"
        first = entries[0][0]
        category = first.get("category", "Components")
        title = first["title"]
        description = first.get("description", "")
        skip = SKIP_SECTIONS.get(f"{relative}.md", {})
        if source is None:
            for entry, _fragment in entries:
                checklist.append({
                    "title": entry["title"], "category": entry.get("category", category),
                    "url": entry["url"], "page": "", "examples": 0, "api_samples": 0,
                    "status": "missing-source",
                    "note": f"no documentation file for {base} in the pinned tag",
                })
            continue
        matter, body = front_matter(source.read_text(encoding="utf-8"))
        sections = split_sections(body)
        page_title = matter.get("title") or title
        document, stats = doc_page(
            title=page_title,
            description=description,
            crumbs=[("Showcase", SHOWCASE_HOME), (category, ""), (page_title, "")],
            sections=sections,
            path=str(out_path.relative_to(ROOT)),
            source_path=f".nds/_source/{source.relative_to(SOURCE).as_posix()}",
            entry=first,
            panel=relative == "components/accessibility",
            skip=skip,
        )
        pages[out_path] = document
        rendered_ids = set(stats["rendered_ids"])
        for entry, fragment in entries:
            if fragment in skip:
                status, note = "excluded-identity", skip[fragment]
            elif fragment and fragment not in rendered_ids:
                status = "source-only"
                note = f"section #{fragment} carries no canonical HTML example of its own"
            elif stats["examples"]:
                status, note = "rendered", ""
            else:
                status = "source-only"
                note = "container/API entry: documented without its own canonical HTML example"
            checklist.append({
                "title": entry["title"],
                "category": entry.get("category", category),
                "url": entry["url"],
                "page": f"/nds-showcase/{relative}.html" + (f"#{fragment}" if fragment else ""),
                "examples": stats["examples"],
                "api_samples": stats["api_samples"],
                "status": status,
                "note": note,
                "shared_page": len(entries) > 1,
            })
    return pages


def build_full_pages(kind: str, checklist: list[dict]) -> dict[pathlib.Path, str]:
    """Render templates/ and examples/ as full pages through the page layout."""
    pages: dict[pathlib.Path, str] = {}
    catalog_name = "templates.yml" if kind == "templates" else "examples.yml"
    catalog_path = SOURCE / "_data" / "content" / catalog_name
    catalog = yaml_list(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else []
    by_url = {entry["url"]: entry for entry in catalog if entry.get("url")}

    for source in sorted((SOURCE / kind).glob("*.md")):
        if source.name == "index.md":
            continue
        text = source.read_text(encoding="utf-8")
        matter, body = front_matter(text)
        relative = f"{kind}/{source.stem}"
        out_path = OUT / f"{relative}.html"
        entry = by_url.get(f"/{relative}.html") or by_url.get(f"/{relative}") or {}
        rendered_body, unresolved = render_source(body, matter)
        missing: set[str] = set()
        rendered_body = localise_assets(rendered_body, missing)
        rendered_body, removed = strip_scripts(rendered_body)
        note = partial_note(unresolved, removed, missing)

        title = matter.get("hero_title") or matter.get("title") or source.stem
        description = matter.get("hero_description") or entry.get("description", "")
        crumbs = [("Showcase", SHOWCASE_HOME), (kind.title(), f"/nds-showcase/{kind}/"), (title, "")]
        layout_class = matter.get("layout_class") or ""
        style = matter.get("hero_style") or ""
        hero = hero_sub(title=title, description=description, crumbs=crumbs, style=style or "nds-flat")
        avatar = ""
        if matter.get("hero_avatar"):
            avatar = f"""      <div class="nds-section-image">
        <div class="nds-avatar nds-image-border">
          <img src="{PLACEHOLDER}" width="120" height="120" alt="">
        </div>
      </div>
"""
        if avatar:
            hero = hero.replace('      <div class="nds-section-head">', avatar + '      <div class="nds-section-head">', 1)

        layout_classes = f"nds-content-layout {layout_class}".strip()
        main = hero + f"""
    <div class="{layout_classes}">
      <div class="nds-main-content" id="main-content">
{note}{nds_shell.indent(rendered_body.strip(), 8)}
      </div>
    </div>
  </main>"""
        parts = [
            chrome_nav(relative, title),
            main,
            nds_shell.indent(chrome_footer(), 2),
            nds_shell.runtime_scripts(page_module=asset("js/site.js")),
        ]
        pages[out_path] = nds_shell.page_document(
            head=chrome_head(title, description, path=str(out_path.relative_to(ROOT))),
            body_class="alq-site",
            parts=parts,
        )
        checklist.append({
            "title": entry.get("title", title),
            "category": kind.title(),
            "url": f"/{relative}.html",
            "page": f"/nds-showcase/{relative}.html",
            "examples": 1,
            "api_samples": 0,
            "status": "partial" if unresolved or removed else "rendered",
            "note": "; ".join(
                filter(None, [
                    f"{len(unresolved)} unresolved Liquid node(s)" if unresolved else "",
                    f"{removed} inline script sample(s) shown as code only" if removed else "",
                    f"{len(missing)} documentation image(s) replaced by a labelled placeholder" if missing else "",
                ])
            ),
        })

    # Category landing pages, so the footer and breadcrumb links resolve.
    for group in ("templates", "examples"):
        entries = [row for row in checklist if row["category"] == group.title()]
        cards = "\n".join(
            f"""            <div class="nds-card nds-stroke alq-full">
              <div class="nds-card-content">
                <div class="nds-card-text">
                  <a class="nds-link nds-primary" href="{row['page']}"><span class="nds-card-title">{html.escape(row['title'])}</span></a>
                  <p class="nds-card-description">{html.escape(row['status'])}{(' — ' + html.escape(row['note'])) if row['note'] else ''}</p>
                </div>
              </div>
            </div>"""
            for row in entries
        )
        section = f"""        <section id="{group}" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-head">
              <h2 class="nds-section-title">{group.title()}</h2>
              <p class="nds-section-description">Full pages generated from the pinned release's
              <code class="nds-inline-code">{group}/*.md</code> sources.</p>
            </div>
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{cards}
              </div>
            </div>
          </div>
        </section>"""
        document, _ = doc_page(
            title=group.title(),
            description=f"Page-level {group} shipped with NDS {VERSION}.",
            crumbs=[("Showcase", SHOWCASE_HOME), (group.title(), "")],
            sections=[],
            path=f"nds-showcase/{group}/index.html",
            source_path=f".nds/_source/{group}/",
        )
        document = document.replace(
            '        <section id="source" class="nds-content-section">',
            section + '\n        <section id="source" class="nds-content-section" hidden>',
            1,
        )
        pages[OUT / group / "index.html"] = document
    return pages


def build_index(checklist: list[dict]) -> str:
    catalog = yaml_list((SOURCE / "_data" / "content" / "components.yml").read_text(encoding="utf-8"))
    rendered = sum(1 for row in checklist if row["status"] == "rendered")
    source_only = sum(1 for row in checklist if row["status"] == "source-only")
    partial = sum(1 for row in checklist if row["status"] == "partial")
    examples = sum(row["examples"] for row in checklist)

    groups: dict[str, list[dict]] = {}
    for entry in catalog:
        groups.setdefault(entry.get("category", "Other"), []).append(entry)

    sections = []
    for category in sorted(groups):
        cards = []
        for entry in groups[category]:
            base, _, fragment = entry["url"].partition("#")
            relative = base.strip("/").replace(".html", "") + (f".html#{fragment}" if fragment else ".html")
            row = next((r for r in checklist if r["url"] == entry["url"] and r["title"] == entry["title"]), None)
            status = row["status"] if row else "not-generated"
            note = row["note"] if row else ""
            status_class = {"rendered": "nds-green", "source-only": "nds-gray", "partial": "nds-yellow"}.get(status, "nds-red")
            cards.append(f"""            <div class="nds-card nds-stroke alq-full">
              <div class="nds-card-content">
                <div class="nds-card-text">
                  <a class="nds-link nds-primary" href="/nds-showcase/{relative}">
                    <span class="nds-card-title">{html.escape(entry['title'])}</span>
                  </a>
                  <p class="nds-card-description">{html.escape(entry.get('description', ''))}</p>
                </div>
                <div class="nds-card-meta">
                  <div class="nds-card-tags">
                    <span class="nds-tag {status_class} nds-sm"><span class="nds-label">{html.escape(status)}</span></span>
                    {f'<span class="nds-tag nds-gray nds-sm"><span class="nds-label">{row["examples"]} examples</span></span>' if row and row['examples'] else ''}
                  </div>
                </div>
              </div>
            </div>""")
        sections.append(f"""        <section id="cat-{re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')}" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-head">
              <h2 class="nds-section-title">{html.escape(category)} <span class="nds-tag nds-gray nds-sm"><span class="nds-label">{len(groups[category])}</span></span></h2>
            </div>
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
              </div>
            </div>
          </div>
        </section>""")

    summary = f"""        <section id="coverage" class="nds-content-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-head">
              <h2 class="nds-section-title">Coverage</h2>
              <p class="nds-section-description">Generated from the pinned release's own catalog:
              <code class="nds-inline-code">.nds/_source/_data/content/components.yml</code>
              ({len(catalog)} entries / {len(groups)} categories). The full checklist is
              <code class="nds-inline-code">docs/NDS-SHOWCASE.md</code>.</p>
            </div>
            <div class="nds-section-body">
              <dl class="nds-definition-list nds-grid alq-facts">
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">Catalog entries</span></dt>
                  <dd>{len(catalog)}</dd>
                </div>
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">Rendered with live examples</span></dt>
                  <dd>{rendered}</dd>
                </div>
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">Container / API entries (source-only)</span></dt>
                  <dd>{source_only}</dd>
                </div>
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">Page templates and examples (partial Liquid)</span></dt>
                  <dd>{partial}</dd>
                </div>
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">Live examples on these pages</span></dt>
                  <dd>{examples}</dd>
                </div>
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt><span class="nds-label">NDS build</span></dt>
                  <dd>v{VERSION} @ {PIN['commit'][:12]}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>"""

    description = (
        f"Review route for NDS v{VERSION}: every catalog entry rendered from the pinned "
        "release's own documentation markup, in light and dark mode, LTR."
    )
    body = hero_sub(
        title=f"NDS {VERSION} component showcase",
        description=description,
        crumbs=[("Showcase", ""), ("Index", "")],
    ) + "\n" + content_layout([summary] + sections, [("coverage", "Coverage")] + [
        (f"cat-{re.sub(r'[^a-z0-9]+', '-', c.lower()).strip('-')}", c) for c in sorted(groups)
    ])
    parts = [
        chrome_nav("index", "Index"),
        body,
        nds_shell.indent(chrome_footer(), 2),
        nds_shell.indent(nds_shell.accessibility_panel("en"), 2),
        nds_shell.runtime_scripts(page_module=asset("js/site.js")),
    ]
    return nds_shell.page_document(
        head=chrome_head("Component showcase", description, path="nds-showcase/index.html"),
        body_class="alq-site",
        parts=parts,
    )


def write_checklist(checklist: list[dict]) -> pathlib.Path:
    catalog = yaml_list((SOURCE / "_data" / "content" / "components.yml").read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = {}
    for row in checklist:
        groups.setdefault(row["category"], []).append(row)
    lines = [
        "# NDS component coverage checklist",
        "",
        f"Generated by `tools/build_showcase.py` from the pinned release catalog",
        f"(`.nds/_source/_data/content/components.yml`, {len(catalog)} entries).",
        f"Do not edit by hand — re-run `python3 tools/build.py`.",
        "",
        f"NDS `{VERSION}` @ `{PIN['commit']}` (tag `{PIN['tag']}`).",
        "",
        "| Category | Entry | Official URL | Showcase page | Live examples | Status | Note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for category in sorted(groups):
        for row in sorted(groups[category], key=lambda item: item["title"]):
            lines.append(
                "| {category} | {title} | `{url}` | {page} | {examples} | {status} | {note} |".format(
                    category=category,
                    title=row["title"],
                    url=row["url"],
                    page=f"[{row['page']}]({row['page']})" if row["page"] else "—",
                    examples=row["examples"],
                    status=row["status"],
                    note=row["note"] or ("shared page" if row.get("shared_page") else ""),
                )
            )
    rows_catalog = [row for row in checklist if row["category"] not in ("Templates", "Examples")]
    rows_pages = [row for row in checklist if row["category"] in ("Templates", "Examples")]
    lines += [
        "",
        "## Summary",
        "",
        f"- Catalog entries: **{len(catalog)}** in {len({row['category'] for row in rows_catalog})} categories.",
        f"- Catalog entries rendered with live canonical examples: **{sum(1 for row in rows_catalog if row['status'] == 'rendered')}**.",
        f"- Container/API entries with no markup of their own: **{sum(1 for row in rows_catalog if row['status'] == 'source-only')}** "
        f"({', '.join(row['title'] for row in rows_catalog if row['status'] == 'source-only')}).",
        f"- Entries deliberately not rendered: **{sum(1 for row in rows_catalog if row['status'] == 'excluded-identity')}** "
        f"({', '.join(row['title'] for row in rows_catalog if row['status'] == 'excluded-identity')}) — government identity on a personal site.",
        f"- Page templates and examples generated: **{len(rows_pages)}** "
        f"({sum(1 for row in rows_pages if row['status'] == 'rendered')} complete, "
        f"{sum(1 for row in rows_pages if row['status'] == 'partial')} labelled partial).",
        f"- Live examples across the showcase: **{sum(row['examples'] for row in checklist)}**.",
        "",
        "## Honest limitations",
        "",
        "- Examples are quoted from the pinned tag's documentation; they are rendered live by the",
        "  project's own NDS runtime, not screenshotted or re-implemented.",
        "- Documentation imagery (`docs-assets/`) and the government identity assets (`assets/img/`,",
        "  `assets/icon/`) are deliberately not shipped; demos that reference them show a labelled",
        "  placeholder (`assets/img/showcase-placeholder.svg`).",
        "- Inline `script` samples are displayed as code and never executed: this site's CSP",
        "  forbids inline scripts.",
        "- Template and example bodies are Jekyll/Liquid. A bounded resolver handles the constructs",
        "  they use; anything else is left as an HTML comment and the row is flagged `partial`.",
        "- Behaviour that depends on an external service (weather widget, real form submission,",
        "  analytics, cookie consent storage) is demonstrated as UI only and labelled as such.",
        "",
    ]
    path = ROOT / "docs" / "NDS-SHOWCASE.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build() -> dict[pathlib.Path, str]:
    if not SOURCE.is_dir():
        raise SystemExit(".nds/_source is missing — run `python3 tools/vendor_nds.py fetch`")
    plan_pages()
    checklist: list[dict] = []
    pages: dict[pathlib.Path, str] = {}
    pages.update(build_catalog_pages(checklist))
    pages.update(build_full_pages("templates", checklist))
    pages.update(build_full_pages("examples", checklist))
    pages[OUT / "index.html"] = build_index(checklist)

    for path, document in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(nds_shell.tidy(document), encoding="utf-8")
    write_checklist(checklist)
    return {path: text for path, text in pages.items()}


if __name__ == "__main__":
    generated = build()
    _policy, hashed = nds_shell.write_csp_for_tree()
    print(f"showcase: {len(generated)} pages under {OUT.relative_to(ROOT)}/; CSP refreshed for {hashed} documents")
