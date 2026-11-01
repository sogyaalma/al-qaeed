#!/usr/bin/env python3
"""Generates the static site from content/content.json with canonical NDS markup.

  python3 tools/build.py

Builds the personal site (Arabic, English, 404, sitemap) and the NDS component
showcase (tools/build_showcase.py), then writes one CSP for every generated page.

Canonical sources (NDS IQ P3 — all read from the pinned tag in .nds/_source/):
  _includes/head.html, head-inline-scripts.html, critical-inline.html   document head
  _sass/_fold.scss ($inline:true)        first-paint gate (compiled by vendor_nds.py)
  _layouts/default.html                  body order + runtime script tags
  ui-shell/mainnav.md                    main navigation (Navigation Bar + actions)
  ui-shell/hero.md, _includes/hero-sub.html   sub hero with portrait
  layout/page-shell.md, layout/section.md     content layout / section tiers
  ui-shell/sideinfo.md, components/toc.md     side info track + manual TOC
  examples/faculty-cv.md                 profile page shape (matched example)
  components/{stepper,cards,definition-list,alert,tags}.md   content components
  _includes/footer.html                  footer
  _includes/accessibility-panel.html     accessibility FAB + panel (verbatim)
  templates/404-template.md              not-found page

Generated: index.html, en/index.html, 404.html, sitemap.xml, nds-showcase/**
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import nds_shell  # noqa: E402
from nds_shell import ASSET_VER, asset, versioned  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "content" / "content.json").read_text(encoding="utf-8"))

LANGS = {
    "ar": {"dir": "rtl", "locale": "ar_SA", "path": "/", "html_lang": "ar"},
    "en": {"dir": "ltr", "locale": "en_US", "path": "/en/", "html_lang": "en"},
}
DEFAULT = DATA["site"]["default_lang"]
SITE_URL = DATA["site"]["url"].rstrip("/")
CV_PATH = "/" + DATA["site"]["cv_file"]
CV_NAME = DATA["site"]["cv_download_name"]
EMAIL = DATA["site"]["email"]
YEAR_FALLBACK = "2026"

# No-JS fallback (documented exception #3): NDS holds JS-inited chrome behind
# `html:not([data-nds-loaded])` (_sass/_skeleton.scss) and has no documented
# no-JavaScript story. These rules release only the regions whose content is
# authored in the HTML and works through native anchors without the runtime.
NOJS_CSS = """<noscript>
      <style>.alq-site :is(.nds-sideinfo, .nds-toc, .nds-drawer),
      .alq-site :is(.nds-sideinfo, .nds-toc, .nds-drawer) > *,
      .alq-site .nds-main-nav > * { visibility: visible; }</style>
    </noscript>"""


def safe_json(value) -> str:
    """Keep JSON data from terminating its HTML script container."""
    return json.dumps(value, ensure_ascii=False, indent=2).replace("<", "\\u003c").replace(
        ">", "\\u003e").replace("&", "\\u0026")


DATE_RANGE = re.compile(r"(\d{4}[\u2013-]\d{4}(\u0647\u0640)?)")


def e(s) -> str:
    escaped = html.escape(str(s), quote=True)
    # Isolate date ranges (e.g. 1437–1444هـ) so both languages show one consistent
    # order and no viewport breaks a range mid-number.
    return DATE_RANGE.sub(r'<span class="nds-ltr alq-date">\1</span>', escaped)


def t(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get(DEFAULT) or ""
    return value


def other_lang(lang):
    return "en" if lang == "ar" else "ar"


def i18n(lang, ar, en):
    return ar if lang == "ar" else en


def content_counts():
    d = DATA
    return {
        "about": len(d["about"]["focus"]),
        "experience": len(d["experience"]["items"]),
        "community": [
            len(d["community"]["groups"]),
            sum(len(g["items"]) for g in d["community"]["groups"]),
        ],
        "skills": len(d["skills"]["groups"]),
        "publications": len(d["publications"]["items"]),
        "education": len(d["education"]["items"]),
        "training": len(d["training"]["items"]),
    }


def validate_nav_counts():
    counts = content_counts()
    problems = []
    for item in DATA["nav"]:
        expected = counts.get(item["id"])
        if expected is None:
            continue
        expected = expected if isinstance(expected, list) else [expected]
        for lang, text in item["meta"].items():
            found = [int(x) for x in re.findall(r"\d+", text)]
            if any(value not in expected for value in found):
                problems.append(f"{item['id']}/{lang}: {found!r} not in {expected!r}")
            if lang == "en" and sorted(found) != sorted(expected):
                problems.append(f"{item['id']}/{lang}: expected {expected!r}, found {found!r}")
    if problems:
        raise SystemExit("Section index counts are stale in content.json:\n  " + "\n  ".join(problems))


def fill_tokens(text, lang):
    counts = content_counts()
    values = {"count": counts["publications"]}
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), str(text))


def page_url(lang):
    return SITE_URL + LANGS[lang]["path"]


# ── head ─────────────────────────────────────────────────────────────────────

def head(lang, title, description, extra_meta="", not_found=False):
    L = LANGS[lang]
    person = DATA["person"]
    alternates = [("x-default", SITE_URL + "/")]
    alternates += [(k, SITE_URL + v["path"]) for k, v in LANGS.items()]
    jsonld = ""
    if not not_found:
        jsonld = (
            '<script type="application/ld+json">'
            + safe_json({
                "@context": "https://schema.org",
                "@type": "Person",
                "name": t(person["name_full"], lang),
                "alternateName": [person["name_short"]["ar"], person["name_short"]["en"]],
                "jobTitle": t(person["title"], lang),
                "description": description,
                "email": f"mailto:{EMAIL}",
                "url": page_url(lang),
                "image": SITE_URL + "/assets/img/portrait.jpg",
                "alumniOf": {
                    "@type": "CollegeOrUniversity",
                    "name": "Imam Muhammad ibn Saud Islamic University",
                },
                "inLanguage": L["html_lang"],
            })
            + "</script>"
        )
    meta = [f'<meta name="theme-color" content="#0e5a49">']
    if not not_found:
        meta += [
            '<meta property="og:type" content="profile">',
            f'<meta property="og:site_name" content="{e(t(person["name_short"], lang))}">',
            f'<meta property="og:title" content="{e(title)}">',
            f'<meta property="og:description" content="{e(description)}">',
            f'<meta property="og:url" content="{e(page_url(lang))}">',
            f'<meta property="og:image" content="{e(SITE_URL + "/assets/img/portrait.jpg")}">',
            f'<meta property="og:image:alt" content="{e(t(person["portrait_alt"], lang))}">',
            f'<meta property="og:locale" content="{L["locale"]}">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
    return nds_shell.document_head(
        lang=L["html_lang"],
        direction=L["dir"],
        title=e(title),
        description=e(description),
        canonical_url=e(page_url(lang)),
        alternates=alternates,
        preload_image=None if not_found else asset("img/portrait-480.webp"),
        extra_meta="\n  ".join(meta + ([extra_meta] if extra_meta else [])),
        jsonld=jsonld,
        head_extra="    " + NOJS_CSS.replace("\n", "\n    "),
    )


# ── chrome ───────────────────────────────────────────────────────────────────

def nav_actions(lang, not_found=False):
    """Documented nav-action patterns: a PAB icon-only link with a hover tooltip."""
    other = other_lang(lang)
    other_label = t(DATA["ui"]["switch_label"], lang)
    other_lang_attr = LANGS[other]["html_lang"]
    href = LANGS[other]["path"]
    dark = i18n(lang, "تبديل الوضع الداكن", "Toggle dark mode")
    language = nds_shell.nav_action_item(
        f"""                <a data-language-switch href="{href}" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-tooltip" data-tooltip-hover="500" title="{e(other_label)}" lang="{other_lang_attr}" hreflang="{other_lang_attr}">
                  <i class="nds-icon nds-hgi-translation" aria-hidden="true"></i>
                  <span class="nds-label" data-hidden="sm md sr">{e(other_label)}</span>
                </a>""",
        extra_class="",
    )
    # components/themes.md → Dark Mode: any button with data-theme-toggle is wired
    # by NDS.Theme (mode flip, persistence, icon swap, circular reveal).
    theme = nds_shell.nav_action_item(
        f"""                <button type="button" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-theme-toggle-wrap nds-tooltip" data-tooltip-hover="500" data-theme-toggle title="{e(dark)}" aria-label="{e(dark)}" aria-pressed="false">
                  <i class="nds-icon nds-hgi-moon-02" aria-hidden="true"></i>
                </button>"""
    )
    return [language, theme]


def body_prelude(lang, not_found=False):
    """Skip link + no-JavaScript navigation (documented exceptions #1 and #3)."""
    ui = DATA["ui"]
    person = DATA["person"]
    home = LANGS[lang]["path"]
    other = other_lang(lang)
    fallback_links = " ".join(
        f'<a href="{home if not_found else ""}#{n["id"]}">{e(t(n["label"], lang))}</a>'
        for n in DATA["nav"]
    )
    return f"""  <a class="alq-skip-link" href="#main-content">{e(t(ui['skip'], lang))}</a>
  <noscript>
    <nav class="alq-fallback" aria-label="{e(i18n(lang, 'التنقل دون جافاسكربت', 'Navigation without JavaScript'))}">
      <a href="{home}">{e(t(person['name_short'], lang))}</a>
      {fallback_links}
      <a data-language-switch href="{LANGS[other]['path']}" lang="{LANGS[other]['html_lang']}" hreflang="{LANGS[other]['html_lang']}">{e(t(ui['switch_label'], lang))}</a>
    </nav>
  </noscript>"""


def header(lang, not_found=False):
    person = DATA["person"]
    home = LANGS[lang]["path"]
    primary = [
        {"href": f"{home if not_found else ''}#{n['id']}", "label": e(t(n["label"], lang))}
        for n in DATA["nav"]
        if n.get("primary")
    ]
    nav = nds_shell.mainnav(
        nav_id="ndsMainNav",
        aria_label=e(i18n(lang, "التنقل الرئيسي", "Primary navigation")),
        brand_href=home,
        brand_logo=asset("img/favicon.svg"),
        brand_name=e(t(person["name_short"], lang)),
        brand_slogan=e(t(person["title"], lang)),
        toggle_label=e(i18n(lang, "فتح قائمة التنقل", "Toggle navigation menu")),
        primary=primary,
        actions=nav_actions(lang, not_found),
    )
    return "  <header>\n" + indent(nav, 4) + "\n  </header>"


indent = nds_shell.indent


def hero(lang):
    """ui-shell/hero.md sub hero with a portrait, as examples/faculty-cv.md uses it."""
    p = DATA["person"]
    ui = DATA["ui"]
    name = t(p["name_short"], lang)
    share_label = i18n(lang, "مشاركة الصفحة", "Share Page")
    copied = i18n(lang, "تم نسخ الرابط!", "Link Copied!")
    copied_message = i18n(lang, "تم نسخ رابط الصفحة إلى الحافظة", "Page link copied to clipboard")
    return f"""    <main>
      <section class="nds-hero-section nds-sub nds-flat" id="top">
        <nav class="nds-breadcrumb-nav" aria-label="{e(i18n(lang, 'مسار التنقل', 'Breadcrumb'))}">
          <ol class="nds-breadcrumb">
            <li><a href="{LANGS[lang]['path']}">{e(i18n(lang, 'الرئيسية', 'Home'))}</a></li>
            <li class="nds-truncate" aria-current="page">{e(name)}</li>
          </ol>
        </nav>
        <div class="nds-section-wrapper">
          <div class="nds-section-image">
            <div class="nds-avatar nds-image-border">
              <img src="{asset('img/portrait-480.webp')}" width="480" height="432" alt="{e(t(p['portrait_alt'], lang))}" fetchpriority="high">
            </div>
          </div>
          <div class="nds-section-head">
            <h1 class="nds-section-title">{e(name)}</h1>
            <p class="nds-section-brief">{e(t(p['title'], lang))}</p>
            <p class="nds-section-description">{e(t(p['tagline'], lang))}</p>
          </div>
          <div class="nds-section-action">
            <a class="nds-btn nds-primary" href="{e(CV_PATH)}" download="{e(CV_NAME)}">
              <i class="hgi hgi-stroke hgi-download-04" aria-hidden="true"></i>
              <span class="nds-label">{e(t(ui['download'], lang))}</span>
            </a>
            <a class="nds-btn nds-secondary-outline" href="#contact">
              <i class="nds-icon nds-hgi-mail-01" aria-hidden="true"></i>
              <span class="nds-label">{e(t(ui['contact_btn'], lang))}</span>
            </a>
            <div class="nds-share nds-dropmenu">
              <button class="nds-btn nds-secondary-outline nds-dropmenu-trigger" type="button" aria-label="{e(share_label)}">
                <i class="nds-icon nds-hgi-share-01" aria-hidden="true"></i>
                <span class="nds-label">{e(share_label)}</span>
              </button>
              <div class="nds-dropmenu-menu" hidden>
                <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-x" type="button" aria-label="{e(i18n(lang, 'المشاركة على X', 'Share on X'))}">
                  <i class="nds-icon nds-hgi-new-twitter" aria-hidden="true"></i>
                  <span class="nds-label">X</span>
                </button>
                <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-linkedin" type="button" aria-label="{e(i18n(lang, 'المشاركة على لينكدإن', 'Share on LinkedIn'))}">
                  <i class="nds-icon nds-hgi-linkedin-02" aria-hidden="true"></i>
                  <span class="nds-label">LinkedIn</span>
                </button>
                <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-whatsapp" type="button" aria-label="{e(i18n(lang, 'المشاركة على واتساب', 'Share on WhatsApp'))}">
                  <i class="nds-icon nds-hgi-whatsapp" aria-hidden="true"></i>
                  <span class="nds-label">WhatsApp</span>
                </button>
                <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-copy" type="button" aria-label="{e(i18n(lang, 'نسخ الرابط', 'Copy Link'))}" data-label="{e(copied)}" data-message="{e(copied_message)}" data-no-auto-close>
                  <i class="nds-icon nds-hgi-link-04" aria-hidden="true"></i>
                  <span class="nds-label">{e(i18n(lang, 'نسخ الرابط', 'Copy Link'))}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>"""


def section_head(title, description=""):
    desc = f'\n            <p class="nds-section-description">{e(description)}</p>' if description else ""
    return f"""          <div class="nds-section-head">
            <h2 class="nds-section-title">{e(title)}</h2>{desc}
          </div>"""


def section_wrapper(section_id, inner):
    return f"""          <div class="nds-section-wrapper" id="{section_id}">
{inner}
          </div>"""


# ── content blocks (examples/faculty-cv.md shape) ────────────────────────────

def about_block(lang):
    a = DATA["about"]
    icons = ["hgi-mosque-01", "hgi-calendar-03", "hgi-user-group", "hgi-book-open-02"]
    facts = []
    for i, fact in enumerate(DATA["hero_facts"]):
        facts.append(
            f"""              <div class="nds-definition-item nds-card nds-stroke">
                <dt>
                  <i class="hgi hgi-stroke {icons[i % len(icons)]}" aria-hidden="true"></i>
                  <span class="nds-label">{e(t(fact['label'], lang))}</span>
                </dt>
                <dd>{e(fill_tokens(t(fact['value'], lang), lang))}</dd>
              </div>"""
        )
    tags = "".join(
        f"""              <span class="nds-tag nds-green nds-sm"><span class="nds-label">{e(t(item['title'], lang))}</span></span>\n"""
        for item in a["focus"]
    )
    focus_notes = "".join(
        f"<p><strong>{e(t(item['title'], lang))}</strong> — {e(t(item['text'], lang))}</p>"
        for item in a["focus"]
    )
    inner = f"""{section_head(t(a['heading'], lang), t(DATA['person']['intro'], lang))}
            <div class="nds-section-body">
              <dl class="nds-definition-list nds-grid alq-facts">
{chr(10).join(facts)}
              </dl>
              <div class="nds-block nds-prose">
                <p>{e(t(a['body'], lang))}</p>
                {focus_notes}
              </div>
              <div class="nds-block">
                <h3 class="nds-block-title">{e(t(a['focus_heading'], lang))}</h3>
                <div class="nds-flex nds-wrap alq-tags">
{tags.rstrip()}
                </div>
              </div>
            </div>"""
    return section_wrapper("about", inner)


def experience_block(lang):
    """components/stepper.md vertical dot stepper.

    faculty-cv.md: `nds-reverse` renders the last step on top, so the markup runs
    oldest-first. content.json is authored most-recent-first; the generator emits
    the canonical order without changing any fact.
    """
    exp = DATA["experience"]
    items = list(reversed(exp["items"]))
    total = len(items)
    steps = []
    for i, item in enumerate(items, start=1):
        note = ""
        if item.get("note"):
            note = f"""
                <ul>
                  <li>{e(t(item['note'], lang))}</li>
                </ul>"""
        steps.append(
            f"""              <div class="nds-stepper-step">
                <div class="nds-stepper-base">
                  <div class="nds-stepper-circle" data-step-text="{i}"></div>
                </div>
                <div class="nds-stepper-content">
                  <div class="nds-divider">{e(t(item['period'], lang))}</div>
                  <div class="nds-stepper-text">
                    <span class="nds-stepper-title">{e(t(item['role'], lang))}</span>
                    <span class="nds-stepper-description">{e(t(item['org'], lang))}</span>
                  </div>{note}
                </div>
              </div>"""
        )
    inner = f"""{section_head(t(exp['heading'], lang), t(exp['intro'], lang))}
            <div class="nds-section-body">
              <div class="nds-stepper nds-vertical nds-dot nds-reverse" data-current="{total}" data-total="{total}">
{chr(10).join(steps)}
              </div>
            </div>"""
    return section_wrapper("experience", inner)


def community_block(lang):
    c = DATA["community"]
    cards = []
    for i, group in enumerate(c["groups"]):
        lis = "".join(f"<li>{e(t(item, lang))}</li>" for item in group["items"])
        # The first group carries the royal appointment: documented elevation
        # modifier instead of a project-specific border/background override.
        emphasis = " nds-shadow" if i == 0 else ""
        cards.append(
            f"""              <div class="nds-card nds-stroke{emphasis} alq-full">
                <div class="nds-card-content">
                  <div class="nds-card-text">
                    <span class="nds-card-title">{e(t(group['title'], lang))}</span>
                    <ul>{lis}</ul>
                  </div>
                </div>
              </div>"""
        )
    achievements = "".join(f"<li>{e(t(item, lang))}</li>" for item in c["achievements"])
    inner = f"""{section_head(t(c['heading'], lang))}
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
              </div>
              <div class="nds-alert nds-card nds-color" data-status="success" role="status">
                <span class="nds-feedback nds-alert-icon nds-outline">
                  <span class="nds-feedback-icon">
                    <i class="nds-icon" aria-hidden="true"></i>
                  </span>
                </span>
                <div class="nds-alert-content">
                  <div class="nds-alert-text">
                    <span class="nds-alert-title">{e(t(c['achievements_heading'], lang))}</span>
                    <ul class="nds-alert-description">{achievements}</ul>
                  </div>
                </div>
              </div>
            </div>"""
    return section_wrapper("community", inner)


def skills_block(lang):
    s = DATA["skills"]
    groups = []
    for group in s["groups"]:
        tags = "".join(
            f'<span class="nds-tag nds-green nds-sm"><span class="nds-label">{e(t(tag, lang))}</span></span>'
            for tag in group["tags"]
        )
        groups.append(
            f"""              <div class="nds-card nds-stroke alq-full">
                <div class="nds-card-content">
                  <div class="nds-card-text">
                    <span class="nds-card-title">{e(t(group['title'], lang))}</span>
                  </div>
                  <div class="nds-flex nds-wrap alq-tags">{tags}</div>
                </div>
              </div>"""
        )
    inner = f"""{section_head(t(s['heading'], lang), t(s['intro'], lang))}
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{chr(10).join(groups)}
              </div>
            </div>"""
    return section_wrapper("skills", inner)


def publications_block(lang):
    p = DATA["publications"]
    cards = []
    for item in p["items"]:
        cards.append(
            f"""              <div class="nds-card nds-stroke nds-rowView alq-full">
                <div class="nds-card-content">
                  <div class="nds-card-text">
                    <span class="nds-card-title">{e(t(item, lang))}</span>
                  </div>
                  <div class="nds-card-meta">
                    <div class="nds-card-tags">
                      <span class="nds-tag nds-green nds-sm"><span class="nds-label">{e(i18n(lang, 'كتيب / بحث', 'Booklet / paper'))}</span></span>
                    </div>
                  </div>
                </div>
              </div>"""
        )
    inner = f"""{section_head(t(p['heading'], lang), t(p['intro'], lang))}
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
              </div>
            </div>"""
    return section_wrapper("publications", inner)


def education_block(lang):
    edu = DATA["education"]
    cards = []
    for item in edu["items"]:
        period = t(item["period"], lang) if item.get("period") else ""
        meta = ""
        if period:
            meta = f"""
                  <div class="nds-card-meta">
                    <div class="nds-card-tags">
                      <span class="nds-tag nds-green nds-rounded nds-sm"><span class="nds-label">{e(period)}</span></span>
                    </div>
                  </div>"""
        cards.append(
            f"""              <div class="nds-card nds-stroke nds-rowView alq-full">
                <div class="nds-card-header">
                  <div class="nds-card-featured-icon">
                    <span class="nds-featured-icon">
                      <i class="hgi hgi-stroke hgi-mortarboard-02" aria-hidden="true"></i>
                    </span>
                  </div>
                </div>
                <div class="nds-card-content">
                  <div class="nds-card-text">
                    <span class="nds-card-title">{e(t(item['title'], lang))}</span>
                    <p class="nds-card-description">{e(t(item['org'], lang))}</p>
                  </div>{meta}
                </div>
              </div>"""
        )
    inner = f"""{section_head(t(edu['heading'], lang))}
            <div class="nds-section-body">
              <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
              </div>
            </div>"""
    return section_wrapper("education", inner)


def training_block(lang):
    tr = DATA["training"]
    lis = "".join(f"<li>{e(t(item, lang))}</li>" for item in tr["items"])
    inner = f"""{section_head(t(tr['heading'], lang))}
            <div class="nds-section-body">
              <div class="nds-card nds-stroke alq-full">
                <div class="nds-card-content">
                  <div class="nds-prose">
                    <ul>{lis}</ul>
                  </div>
                </div>
              </div>
            </div>"""
    return section_wrapper("training", inner)


def contact_block(lang):
    c = DATA["contact"]
    ui = DATA["ui"]
    inner = f"""{section_head(t(c['heading'], lang), t(c['text'], lang))}
            <div class="nds-section-action">
              <a class="nds-btn nds-primary" href="mailto:{e(EMAIL)}">
                <i class="nds-icon nds-hgi-mail-01" aria-hidden="true"></i>
                <span class="nds-label">{e(t(ui['email_btn'], lang))}</span>
              </a>
              <a class="nds-btn nds-secondary-outline" href="{e(CV_PATH)}" download="{e(CV_NAME)}">
                <i class="hgi hgi-stroke hgi-download-04" aria-hidden="true"></i>
                <span class="nds-label">{e(t(ui['download'], lang))}</span>
              </a>
            </div>
            <div class="nds-section-body">
              <dl class="nds-definition-list nds-grid alq-facts-single">
                <div class="nds-definition-item nds-card nds-stroke">
                  <dt>
                    <i class="hgi hgi-stroke hgi-mail-01" aria-hidden="true"></i>
                    <span class="nds-label">{e(t(c['email_label'], lang))}</span>
                  </dt>
                  <dd><a class="nds-link nds-primary" href="mailto:{e(EMAIL)}"><span class="nds-ltr">{e(EMAIL)}</span></a></dd>
                </div>
              </dl>
            </div>"""
    return section_wrapper("contact", inner)


# Extension point for a future section: one bilingual object in content.json,
# one nav entry whose id matches the section wrapper, and one renderer here.
# Do not add an empty placeholder section or invented biography.
PROFILE_SECTIONS = (
    ("about", about_block),
    ("experience", experience_block),
    ("community", community_block),
    ("skills", skills_block),
    ("publications", publications_block),
    ("education", education_block),
    ("training", training_block),
    ("contact", contact_block),
)


def content_layout(lang):
    """layout/page-shell.md: nds-content-layout.nds-wSideInfo > nds-main-content."""
    missing = [key for key, _render in PROFILE_SECTIONS if key not in DATA]
    if missing:
        raise SystemExit(
            "PROFILE_SECTIONS names content that content.json does not have: " + ", ".join(missing)
        )
    name = t(DATA["person"]["name_short"], lang)
    toc_links = "\n".join(
        f"""                <li>
                  <a href="#{n['id']}" class="nds-btn nds-subtle nds-indicator">
                    <span class="nds-label nds-truncate">{e(t(n['label'], lang))}</span>
                  </a>
                </li>"""
        for n in DATA["nav"]
    )
    blocks = "\n".join(render(lang) for _key, render in PROFILE_SECTIONS)
    return f"""      <div class="nds-content-layout nds-wSideInfo">
        <div class="nds-main-content" id="main-content">
          <section id="profile" class="nds-content-section nds-sideinfo-section">
            <div class="nds-section-body">
              <aside class="nds-sideinfo nds-md nds-sticky nds-top" aria-label="{e(i18n(lang, 'في هذه الصفحة', 'On this page'))}">
                <nav class="nds-toc alq-toc" aria-label="{e(t(DATA['ui']['index_aria'], lang))}">
                  <div class="nds-toc-head">
                    <span class="nds-label">{e(i18n(lang, 'في هذه الصفحة', 'On this page'))}</span>
                    <h2 class="nds-toc-title nds-truncate">{e(name)}</h2>
                  </div>
                  <div class="nds-drawer nds-lined">
                    <ul class="nds-drawer-list">
{toc_links}
                    </ul>
                  </div>
                </nav>
              </aside>
              <div class="nds-info-content">
{blocks}
              </div>
            </div>
          </section>
          <section class="nds-last-edit nds-content-section">
            {e(t(DATA['ui']['updated_note'], lang))}
          </section>
        </div>
      </div>
    </main>"""


def footer(lang, not_found=False, showcase=False):
    ui = DATA["ui"]
    person = DATA["person"]
    name = t(person["name_short"], lang)
    prefix = LANGS[lang]["path"] if not_found else ""
    columns = [
        {
            "heading": e(i18n(lang, "أقسام الصفحة", "Page sections")),
            "links": [
                {"href": f"{prefix}#{n['id']}", "label": e(t(n["label"], lang))} for n in DATA["nav"]
            ],
        },
        {
            "heading": e(t(DATA["contact"]["heading"], lang)),
            "links": [
                {"href": f"mailto:{e(EMAIL)}", "label": e(EMAIL), "icon": "nds-hgi-mail-01"},
                {
                    # The pinned release registers no file/download UI icon
                    # (76-entry catalog), and _includes/footer.html always prefixes
                    # `nds-icon`, so this link carries its label only.
                    "href": e(CV_PATH),
                    "label": e(t(ui["download"], lang)),
                },
            ],
        },
    ]
    if showcase:
        columns.append({
            "heading": e(i18n(lang, "المعرض", "Showcase")),
            "links": [{"href": "/nds-showcase/", "label": e(i18n(lang, "فهرس المكونات", "Component index"))}],
        })
    return nds_shell.footer(
        aria_label=e(i18n(lang, "تذييل الموقع", "Site Footer")),
        nav_label=e(i18n(lang, "تنقل التذييل", "Footer navigation")),
        columns=columns,
        copyright_text=f"{e(name)} &copy; {YEAR_FALLBACK}. {e(t(ui['footer_rights'], lang))}",
    )


# ── pages ────────────────────────────────────────────────────────────────────

def page(lang):
    seo = DATA["seo"][lang]
    parts = [
        body_prelude(lang),
        header(lang),
        hero(lang) + "\n" + content_layout(lang),
        indent(footer(lang), 2),
        indent(nds_shell.accessibility_panel(lang), 2),
        nds_shell.runtime_scripts(page_module=asset("js/site.js")),
    ]
    return nds_shell.page_document(
        head=head(lang, seo["title"], seo["description"]),
        body_class="alq-site",
        parts=parts,
    )


def page_404():
    title = "404 | الصفحة غير موجودة"
    head_html = head(
        "ar", title, "الصفحة غير موجودة",
        extra_meta='<meta name="robots" content="noindex">', not_found=True,
    )
    main_html = f"""  <main>
      <div class="nds-content-layout">
        <div class="nds-main-content" id="main-content">
          <section id="not-found" class="nds-content-section nds-status-section">
            <div class="nds-section-wrapper">
              <div class="nds-section-image">
                <img src="{asset('img/404-mark.svg')}" width="458" height="324" alt="">
              </div>
              <div class="nds-section-head">
                <h1 class="nds-section-title">الصفحة غير موجودة</h1>
                <p class="nds-section-description">الرابط الذي فتحته غير موجود أو تم نقله.</p>
              </div>
              <div class="nds-section-action">
                <a href="/" class="nds-btn nds-primary"><span class="nds-label">الصفحة الرئيسية</span></a>
                <a href="/en/" class="nds-btn nds-secondary-outline" lang="en"><span class="nds-label">English</span></a>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>"""
    parts = [
        body_prelude("ar", not_found=True),
        header("ar", not_found=True),
        main_html,
        indent(footer("ar", not_found=True), 2),
        indent(nds_shell.accessibility_panel("ar"), 2),
        nds_shell.runtime_scripts(page_module=asset("js/site.js")),
    ]
    return nds_shell.page_document(head=head_html, body_class="alq-site", parts=parts)


def sitemap():
    urls = []
    for lang, meta in LANGS.items():
        loc = SITE_URL + meta["path"]
        alts = "\n".join(
            f'    <xhtml:link rel="alternate" hreflang="{k}" href="{e(SITE_URL + v["path"])}"/>'
            for k, v in LANGS.items()
        )
        urls.append(
            f"""  <url>
    <loc>{e(loc)}</loc>
{alts}
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}/"/>
  </url>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{chr(10).join(urls)}
</urlset>
"""


def validate_config():
    origin = urlsplit(SITE_URL)
    if origin.scheme != "https" or not origin.netloc or origin.path or origin.query or origin.fragment or origin.username:
        raise SystemExit("site.url must be an HTTPS origin without credentials, path, query or fragment")
    cv = pathlib.PurePosixPath(DATA["site"]["cv_file"])
    if cv.is_absolute() or ".." in cv.parts or cv.parts[:2] != ("assets", "docs"):
        raise SystemExit("site.cv_file must be a relative path inside assets/docs/")
    if DEFAULT not in LANGS:
        raise SystemExit("Unsupported default language")
    for item in DATA["nav"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", item["id"]):
            raise SystemExit("Navigation IDs must be stable ASCII slugs")


def build_site() -> list[pathlib.Path]:
    validate_config()
    validate_nav_counts()
    written = []
    for path, text in (
        (ROOT / "index.html", page("ar")),
        (ROOT / "en" / "index.html", page("en")),
        (ROOT / "404.html", page_404()),
        (ROOT / "sitemap.xml", sitemap()),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(nds_shell.tidy(text), encoding="utf-8")
        written.append(path)
    return written


def main():
    written = build_site()

    # The showcase quotes the pinned release's own documentation, so it needs
    # NDS_ROOT. The personal site does not: its chrome comes from the committed
    # copies in tools/generated/. That keeps an offline build of the site possible
    # and makes the showcase's provenance requirement explicit.
    showcase_count = 0
    if (ROOT / ".nds" / "_source").is_dir():
        import build_showcase

        showcase_count = len(build_showcase.build())
    else:
        print(
            "note: .nds/_source is not installed, so /nds-showcase/ was left as "
            "committed. Run `python3 tools/vendor_nds.py fetch` to regenerate it."
        )

    policy, hashed = nds_shell.write_csp_for_tree()
    print(
        f"Built {len(written)} site files and {showcase_count} showcase pages "
        f"(NDS {ASSET_VER}); CSP hashes refreshed for {hashed} HTML documents."
    )


if __name__ == "__main__":
    main()
