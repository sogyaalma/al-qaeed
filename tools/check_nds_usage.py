#!/usr/bin/env python3
"""Verifies every NDS hook in the generated pages exists in the pinned release.

  python3 tools/check_nds_usage.py            # checks the generated site + showcase

Guards NDS IQ hard rule #2 (never invent NDS APIs, selectors, options or markup)
and the provenance rule that markup and runtime come from the same release:

  1. every `nds-*` / `hgi-*` class in a generated page exists in the shipped NDS
     CSS or runtime JS, or is an explicitly documented project class;
  2. every `nds-hgi-*` icon token is registered in the pinned release's icon
     catalog (`.nds/_source/_data/content/icons.yml`);
  3. every `hgi hgi-stroke hgi-*` font glyph has a rule in the shipped HGI sheet;
  4. every `data-*` hook used on an NDS element is one the runtime reads.

Exit code 1 on any finding, so CI can gate on it.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".nds" / "_source"

# Project-owned classes (docs/CUSTOM-EXCEPTIONS.md). Anything else with an
# `nds-`/`hgi-` prefix must come from the pinned release.
PROJECT_CLASSES = {
    "alq-site", "alq-skip-link", "alq-fallback", "alq-date", "alq-nowrap",
    # CSP knob conversions of canonical inline custom properties (IQ edit #4).
    "alq-facts", "alq-facts-single", "alq-full", "alq-stack", "alq-tags", "alq-toc",
}

# Tokens the pinned release uses in its own documentation or demo data but does
# not style or script. Quoted verbatim (never invented here) and reported, because
# the mismatch belongs to the release, not to this project:
#   nds-purple — `_data/content/faqs.yml` sets `color: purple` for FAQ tags, while
#   `_sass/components/_tags.scss` in v1.12.0 ships only blue, gray, green, neutral,
#   red and yellow. The tag renders with the component's default colour.
UPSTREAM_DISCREPANCIES = {
    "nds-purple": "used by the release's own faqs.yml demo data; v1.12.0 _tags.scss ships blue/gray/green/neutral/red/yellow only",
}

# data-* hooks the runtime reads, gathered from the pinned JS sources.
DATA_HOOK_ALLOWLIST_EXTRA = {
    "data-language-switch",  # project hook (assets/js/site.js)
    "data-step-text", "data-no-auto-close", "data-tooltip-hover", "data-tooltip-message",
    "data-hidden", "data-calendar", "data-theme-toggle", "data-theme-value",
    "data-panel-toggle", "data-panel-side", "data-fab-pos", "data-a11y-mode",
    "data-a11y-setting", "data-a11y-visual", "data-i18n", "data-i18n-attr",
    "data-current", "data-total", "data-status", "data-rating", "data-label",
    "data-message", "data-toc-source", "data-nds-defer", "data-palette",
}


def shipped_class_names() -> set[str]:
    """Classes the pinned release styles or scripts, plus its own chrome markup."""
    names: set[str] = set()
    for path in sorted((ROOT / "assets" / "css").glob("*.css")):
        if path.name == "theme.css":
            continue
        names.update(re.findall(r"\.((?:nds|hgi)-[A-Za-z0-9_-]+)", path.read_text(encoding="utf-8", errors="replace")))
    for path in sorted((ROOT / "assets" / "js").glob("*.min.js")):
        names.update(re.findall(r"((?:nds|hgi)-[A-Za-z0-9_-]+)", path.read_text(encoding="utf-8", errors="replace")))
    # Includes and layouts carry hooks that are canonical without being styled
    # (e.g. nds-theme-toggle-wrap in _includes/topbar.html).
    for folder in ("_includes", "_layouts"):
        for path in sorted((SOURCE / folder).glob("*.html")):
            for match in re.finditer(r'\bclass="([^"]*)"', path.read_text(encoding="utf-8", errors="replace")):
                names.update(match.group(1).split())
    return names


def documented_class_names() -> set[str]:
    """Classes the pinned release documents in its own example markup.

    The showcase quotes those blocks verbatim, so a class the documentation uses
    (for example `nds-responsive` on a docs table) is upstream's, not an invention
    of this project. Counted separately and reported, never silently merged.
    """
    names: set[str] = set()
    for path in sorted(SOURCE.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'class="([^"]*)"', html.unescape(text)):
            names.update(match.group(1).split())
        for match in re.finditer(r'&lt;i class=&quot;([^&]*)&quot;', text):
            names.update(html.unescape(match.group(1)).split())
    return {name for name in names if name.startswith(("nds-", "hgi-"))}


def project_classes() -> set[str]:
    theme = ROOT / "assets" / "css" / "theme.css"
    return PROJECT_CLASSES | set(re.findall(r"\.(alq-[A-Za-z0-9_-]+)", theme.read_text(encoding="utf-8")))


def icon_tokens() -> set[str]:
    catalog = SOURCE / "_data" / "content" / "icons.yml"
    text = catalog.read_text(encoding="utf-8")
    return set(re.findall(r"\bnds-hgi-[A-Za-z0-9-]+", text))


def hgi_glyphs() -> set[str]:
    sheet = ROOT / "assets" / "css" / "hgi-rounded-stroke-min.css"
    return set(re.findall(r"\.hgi-stroke\.(hgi-[A-Za-z0-9-]+):before", sheet.read_text(encoding="utf-8")))


def documented_hooks() -> set[str]:
    """data-* attributes the release's own documentation markup carries.

    Several examples are wired by the docs site's own demo script
    (`nds-showcase.min.js`), which this project deliberately does not ship, so the
    hook is inert here. Allowed on showcase pages only, counted and reported, and
    the generated page labels the example — never silently presented as working.
    """
    hooks: set[str] = set()
    for path in sorted(SOURCE.rglob("*.md")):
        hooks.update(re.findall(r"\bdata-[a-z0-9-]+", html.unescape(path.read_text(encoding="utf-8", errors="replace"))))
    return hooks


def runtime_hooks() -> set[str]:
    hooks = set(DATA_HOOK_ALLOWLIST_EXTRA)
    for path in sorted((SOURCE / "_js").glob("*.js")):
        text = path.read_text(encoding="utf-8", errors="replace")
        hooks.update(re.findall(r"\bdata-[a-z0-9-]+", text))
    for path in sorted((SOURCE / "_includes").glob("*.html")):
        hooks.update(re.findall(r"\bdata-[a-z0-9-]+", path.read_text(encoding="utf-8", errors="replace")))
    for path in sorted((ROOT / "assets" / "js").glob("*.js")):
        hooks.update(re.findall(r"\bdata-[a-z0-9-]+", path.read_text(encoding="utf-8", errors="replace")))
    return hooks


def pages() -> list[pathlib.Path]:
    found = [ROOT / name for name in ("index.html", "404.html")]
    found += sorted((ROOT / "en").glob("*.html"))
    found += sorted((ROOT / "nds-showcase").rglob("*.html"))
    return [path for path in found if path.is_file()]


def main() -> int:
    if not SOURCE.is_dir():
        print("SKIP .nds/_source is missing; run `python3 tools/vendor_nds.py fetch`.")
        return 0

    shipped = shipped_class_names()
    documented = documented_class_names()
    docs_only: set[str] = set()
    discrepancies: set[str] = set()
    owned = project_classes()
    icons = icon_tokens()
    glyphs = hgi_glyphs()
    hooks = runtime_hooks()
    documented_data = documented_hooks()
    inert_hooks: set[str] = set()

    findings: list[str] = []
    counts = {"pages": 0, "classes": set(), "icons": set(), "glyphs": set(), "hooks": set()}

    for path in pages():
        text = path.read_text(encoding="utf-8")
        counts["pages"] += 1
        relative = path.relative_to(ROOT).as_posix()

        showcase_page = relative.startswith("nds-showcase/")
        for match in re.finditer(r'\bclass="([^"]*)"', text):
            for name in match.group(1).split():
                if not name.startswith(("nds-", "hgi-", "alq-")):
                    continue
                counts["classes"].add(name)
                if name in shipped or name in owned:
                    continue
                # Quoted documentation markup may use a docs-only class; on the
                # personal site pages nothing but the release itself is accepted.
                if showcase_page and name in documented:
                    docs_only.add(name)
                    continue
                if showcase_page and name in UPSTREAM_DISCREPANCIES:
                    discrepancies.add(name)
                    continue
                findings.append(f"{relative}: unknown class .{name}")

        for match in re.finditer(r"\bnds-hgi-[A-Za-z0-9-]+", text):
            token = match.group(0)
            counts["icons"].add(token)
            if token not in icons:
                findings.append(f"{relative}: icon token {token} is not in the pinned catalog")

        for match in re.finditer(r'class="hgi hgi-stroke (hgi-[A-Za-z0-9-]+)"', text):
            glyph = match.group(1)
            counts["glyphs"].add(glyph)
            if glyph not in glyphs:
                findings.append(f"{relative}: HGI glyph {glyph} has no rule in the shipped sheet")

        for match in re.finditer(r"\b(data-[a-z0-9-]+)=", text):
            hook = match.group(1)
            counts["hooks"].add(hook)
            if hook in hooks:
                continue
            if showcase_page and hook in documented_data:
                inert_hooks.add(hook)
                continue
            findings.append(f"{relative}: data hook {hook} is not read by the pinned runtime")

    if inert_hooks:
        print(
            f"note: {len(inert_hooks)} data hook(s) belong to the release's docs demo layer, "
            "which this project does not ship; those examples are labelled inert on their page: "
            + ", ".join(sorted(inert_hooks))
        )
    if docs_only:
        print(
            f"note: {len(docs_only)} class(es) appear only in the release's own documentation "
            "markup and have no rule in the shipped CSS/JS; they are quoted verbatim: "
            + ", ".join(sorted(docs_only))
        )
    if discrepancies:
        print(
            f"note: {len(discrepancies)} release discrepancy(ies) quoted as published: "
            + "; ".join(f"{name} — {UPSTREAM_DISCREPANCIES[name]}" for name in sorted(discrepancies))
        )
    print(
        f"scanned {counts['pages']} pages: {len(counts['classes'])} classes, "
        f"{len(counts['icons'])} icon tokens, {len(counts['glyphs'])} HGI glyphs, "
        f"{len(counts['hooks'])} data hooks"
    )
    unique = sorted(set(findings))
    if unique:
        print(f"FAIL {len(unique)} finding(s):")
        for line in unique[:60]:
            print("  " + line)
        if len(unique) > 60:
            print(f"  … {len(unique) - 60} more")
        return 1
    print("PASS every NDS hook in the generated pages exists in the pinned release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
