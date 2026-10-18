#!/usr/bin/env python3
"""
Generates the static pages from content/content.json using NDS-vanilla markup.

  python3 tools/build.py

Canonical sources (NDS IQ):
  examples/faculty-cv.md          — profile page shape
  layout/page-layout.md           — article + sideinfo body
  ui-shell/hero.md #hero-profile  — sub/flat hero with avatar
  ui-shell/mainnav.md             — header navigation
  ui-shell/footer.md              — footer
  templates/404-template.md       — not-found page
  ui-shell/head.md                — document head (preloads + bootstrap, blocking noscript CSS)

Generated:
  index.html, en/index.html, 404.html, sitemap.xml
"""
import html
import base64
import hashlib
import json
import pathlib
import re
from urllib.parse import urlsplit

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
ASSET_VER = "1.12.x-dev"

# Inline gate from ui-shell/head.md (required first-paint hide until NDS CSS).
GATE_CSS = """html[data-theme~=dark] :where(.nds-main-nav .nds-brand.nds-oncolor :is(img,svg)){filter:brightness(0) invert(1)}
    html{background-color:var(--background-body, #f8f5ee)}
    html[data-theme~=dark]{background-color:var(--background-body, #111927)}
    :where(.nds-topbar){background-color:var(--background-topbar, #f3f4f6)}
    html[data-theme~=dark] :where(.nds-topbar){background-color:var(--background-topbar, #111927)}
    :where(.nds-main-nav){background-color:var(--background-nav, #fffdf8)}
    html[data-theme~=dark] :where(.nds-main-nav){background-color:var(--background-nav, #1f2a37)}
    :where(.nds-hero-image-wrapper)::before{content:"";position:absolute;inset:0;background:color-mix(in srgb, var(--background-image-overlay, #0a3d32) calc(var(--overlay, 0.7) * 100%), transparent);pointer-events:none}
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    html{overflow-anchor:none}
    html :where(header){display:contents}
    html :where(.nds-topbar){height:40px}
    html :where(.nds-main-nav){height:var(--nds-nav-height, 72px)}
    html .nds-swiper.nds-hero:not([data-nds-swiper-initialized],[data-swiper-preset]) .nds-swiper-slide:not(:first-child){display:none}
    :where(.nds-topbar>*,.nds-main-nav>*,.nds-hero-section .nds-section-action,.nds-content-layout,.nds-user-feedback-section,.nds-footer){visibility:hidden}
    html:not([data-nds-loaded]) main{overflow-x:clip}
    .nds-skip-link:not(:focus){position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0, 0, 0, 0);white-space:nowrap;border:0}
    :root{--nds-icons-opacity: 0}
    :is(.nds-hidden,[hidden],[data-state~=hidden],[data-filtered]){display:none !important}
    :where(.nds-hero-section){position:relative;height:550px}
    :where(.nds-hero-section.nds-sub){height:auto;min-height:220px}
    :where(.nds-hero-image-wrapper){position:absolute;inset:0}
    :where(.nds-hero-image){width:100%;height:100%;object-fit:cover;display:block}
    :where(.nds-hero-section :is(.nds-section-body,.nds-section-wrapper,.nds-breadcrumb-nav)){visibility:hidden}"""

THEME_BOOT = """(function() {
      var v; try { v = localStorage.getItem('nds-theme'); } catch (e) {}
      if (v) {
        var d = document.documentElement;
        var t = ((d.getAttribute('data-theme') || '') + ' ' + v).split(/\\s+/)
          .filter(function (x, i, a) { return x && a.indexOf(x) === i; });
        d.setAttribute('data-theme', t.join(' '));
      }
    })();
    (function () {
      document.querySelectorAll('link[rel="preload"][data-nds-defer]').forEach(function (p) {
        var l = document.createElement('link');
        for (var i = 0; i < p.attributes.length; i++) {
          var a = p.attributes[i];
          if (a.name !== 'rel' && a.name !== 'as') l.setAttribute(a.name, a.value);
        }
        l.rel = 'stylesheet';
        p.removeAttribute('data-nds-defer');
        document.head.appendChild(l);
      });
    })();"""


def safe_json(value):
    """Keep JSON data from terminating its HTML script container."""
    return json.dumps(value, ensure_ascii=False, indent=2).replace("<", "\\u003c").replace(
        ">", "\\u003e").replace("&", "\\u0026")


def write_csp(pages):
    """Refresh only the CSP line; preserve other owner-maintained headers."""
    def hashes(tag):
        bodies = {m.group(1) for page in pages for m in re.finditer(
            rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", page, re.S) if m.group(1).strip()}
        return " ".join("'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
                        + "'" for body in sorted(bodies))
    policy = ("default-src 'self'; img-src 'self' data:; font-src 'self'; "
              "style-src 'self' " + hashes("style") + "; style-src-attr 'unsafe-inline'; "
              "script-src 'self' " + hashes("script") + "; script-src-attr 'none'; "
              "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
    path = ROOT / "_headers"
    headers = path.read_text(encoding="utf-8")
    headers, count = re.subn(r"(?m)^  Content-Security-Policy:.*$",
                            "  Content-Security-Policy: " + policy, headers)
    if count != 1:
        raise SystemExit("Expected exactly one CSP header in _headers")
    path.write_text(headers, encoding="utf-8")
    # Vercel remains an optional static host with identical security policy.
    vercel_path = ROOT / "vercel.json"
    vercel = json.loads(vercel_path.read_text(encoding="utf-8"))
    for rule in vercel["headers"]:
        for header in rule["headers"]:
            if header["key"] == "Content-Security-Policy":
                header["value"] = policy
    vercel_path.write_text(json.dumps(vercel, indent=2) + "\n", encoding="utf-8")


def e(s):
    return html.escape(str(s), quote=True)


def t(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get(DEFAULT) or ""
    return value


def other_lang(lang):
    return "en" if lang == "ar" else "ar"


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


def i18n(lang, ar, en):
    return ar if lang == "ar" else en


def head(lang, title, description, extra_meta="", not_found=False):
    L = LANGS[lang]
    person = DATA["person"]
    name = t(person["name_short"], lang)
    alt_links = chr(10).join(
        f'  <link rel="alternate" hreflang="{k}" href="{e(SITE_URL + v["path"])}">' for k, v in LANGS.items()
    )
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": t(person["name_full"], lang),
        "alternateName": [DATA["person"]["name_short"]["ar"], DATA["person"]["name_short"]["en"]],
        "jobTitle": t(person["title"], lang),
        "description": description,
        "email": f"mailto:{EMAIL}",
        "url": page_url(lang),
        "image": SITE_URL + "/assets/img/portrait.jpg",
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Imam Muhammad ibn Saud Islamic University"},
        "inLanguage": L["html_lang"],
    }
    return f"""<!DOCTYPE html>
<html lang="{L['html_lang']}" dir="{L['dir']}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(title)}</title>
  <style>
    {GATE_CSS}
  </style>
  {'' if not_found else '<link rel="preload" as="image" href="/assets/img/portrait-480.webp" fetchpriority="high">'}
  <link rel="preload" href="/assets/css/nds.critical.min.css?ver={ASSET_VER}" as="style" fetchpriority="high" data-nds-defer>
  <link rel="preload" href="/assets/css/nds-main.min.css?ver={ASSET_VER}" as="style" fetchpriority="low" data-nds-defer="main">
  <link rel="preload" href="/assets/css/theme.css?ver={ASSET_VER}" as="style" data-nds-defer>
  <link rel="icon" type="image/svg+xml" href="/assets/img/favicon.svg" fetchpriority="low">
  <meta name="description" content="{e(description)}">
  <meta name="theme-color" content="#0e5a49">
  <link rel="canonical" href="{e(page_url(lang))}">
  <link rel="alternate" hreflang="x-default" href="{e(SITE_URL + '/')}">
{alt_links}
  <meta property="og:type" content="profile">
  <meta property="og:site_name" content="{e(name)}">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{e(page_url(lang))}">
  <meta property="og:image" content="{e(SITE_URL + '/assets/img/portrait.jpg')}">
  <meta property="og:image:alt" content="{e(t(person['portrait_alt'], lang))}">
  <meta property="og:locale" content="{L['locale']}">
  <meta name="twitter:card" content="summary_large_image">
  {extra_meta}
  {'' if not_found else '<script type="application/ld+json">' + safe_json(jsonld) + '</script>'}
  <script>
    {THEME_BOOT}
  </script>
  <noscript>
    <link rel="stylesheet" href="/assets/css/nds.critical.min.css?ver={ASSET_VER}">
    <link rel="stylesheet" href="/assets/css/nds-main.min.css?ver={ASSET_VER}">
    <link rel="stylesheet" href="/assets/css/theme.css?ver={ASSET_VER}">
    <style>:where(.nds-topbar>*,.nds-main-nav>*,.nds-hero-section .nds-section-action,.nds-content-layout,.nds-footer,.nds-hero-section :is(.nds-section-body,.nds-section-wrapper,.nds-breadcrumb-nav)){{visibility:visible}}
    .alq-site .nds-main-nav,.alq-site .nds-breadcrumb-nav,.alq-site .nds-sideinfo,.alq-site .nds-share{{display:none !important}}
    .alq-site .nds-sideinfo-section > .nds-section-body{{display:block}}
    /* NDS's pre-init card/definition skeletons never release without JS.
       Scoped no-JS adaptation: preserve readable authored text, not fake init state. */
    .alq-site .nds-card,.alq-site .nds-definition-list{{animation:none !important}}
    .alq-site #main-content .nds-card :is(.nds-card-title,.nds-card-subtitle,.nds-card-description,.nds-tag,.nds-label),
    .alq-site #main-content .nds-definition-list :is(dt,dd,dt *,dd *){{color:var(--text-default) !important;background:none !important}}
    .alq-site #main-content .nds-card .nds-tag > *{{visibility:visible !important}}
    .alq-site .nds-content-section{{content-visibility:visible;contain-intrinsic-size:none}}
    .alq-fallback{{display:flex;flex-wrap:wrap;gap:12px;padding:16px;background:#fffdf8;color:#15201c}}
    .alq-fallback a{{display:inline-flex;align-items:center;min-height:44px;padding:8px;color:#0e5a49}}</style>
  </noscript>
</head>
"""


def header(lang, not_found=False):
    ui = DATA["ui"]
    other = other_lang(lang)
    home = LANGS[lang]["path"]
    name = t(DATA["person"]["name_short"], lang)
    slogan = t(DATA["person"]["title"], lang)
    other_label = t(ui["switch_label"], lang)
    other_lang_attr = LANGS[other]["html_lang"]
    nav_items = []
    for n in DATA["nav"]:
        if not n.get("primary"):
            continue
        nav_items.append(
            f"""          <li class="nds-nav-item">
            <a href="{home if not_found else ''}#{n['id']}" class="nds-nav-link nds-btn nds-subtle nds-indicator">
              <span class="nds-label">{e(t(n['label'], lang))}</span>
            </a>
          </li>"""
        )
    links = chr(10).join(nav_items)
    fallback_links = " ".join(
        f'<a href="{home if not_found else ""}#{n["id"]}">{e(t(n["label"], lang))}</a>'
        for n in DATA["nav"]
    )
    skip = t(ui["skip"], lang)
    toggle = i18n(lang, "فتح قائمة التنقل", "Toggle navigation menu")
    return f"""<body class="alq-site">
  <a class="nds-skip-link" href="#main-content">{e(skip)}</a>
  <noscript>
    <nav class="alq-fallback" aria-label="{e(i18n(lang, 'التنقل دون جافاسكربت', 'Navigation without JavaScript'))}">
      <a href="{home}">{e(name)}</a>
      {fallback_links}
      <a data-language-switch href="{LANGS[other]['path']}" lang="{other_lang_attr}" hreflang="{other_lang_attr}">{e(other_label)}</a>
    </nav>
  </noscript>
  <header>
    <nav class="nds-main-nav nds-content-wrapper" id="nds-main-nav" aria-label="{e(i18n(lang, 'التنقل الرئيسي', 'Primary navigation'))}" data-i18n-aria-label="mainnav.primary_navigation">
      <div class="nds-nav-container">
        <a href="{home}" class="nds-brand">
          <img class="nds-brand-logo" src="/assets/img/favicon.svg" width="40" height="40" alt="">
          <span class="nds-brand-name">{e(name)}
            <span class="nds-brand-slogan">{e(slogan)}</span>
          </span>
        </a>
        <ul class="nds-nav-minimal" hidden>
          <li class="nds-nav-toggler nds-nav-item">
            <button type="button" class="nds-nav-link nds-btn nds-subtle nds-indicator" aria-label="{e(toggle)}" data-i18n-aria-label="mainnav.toggle_menu" aria-expanded="false" aria-controls="nds-nav-collapse">
              <i class="nds-icon nds-hgi-menu-01" aria-hidden="true"></i>
            </button>
          </li>
        </ul>
        <div class="nds-nav-collapse" id="nds-nav-collapse" hidden>
          <div class="nds-nav-collapse-content">
            <ul class="nds-nav-primary">
{links}
            </ul>
            <div class="nds-nav-item nds-show-more">
              <a href="{home if not_found else ''}#about" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-full" title="{e(i18n(lang, 'المزيد', 'Show more'))}" data-i18n-title="scroll-more.show_more" aria-label="{e(i18n(lang, 'المزيد', 'Show more'))}" data-i18n-aria-label="scroll-more.show_more">
                <i class="nds-icon nds-hgi-arrow-down-01" aria-hidden="true"></i>
              </a>
            </div>
            <ul class="nds-nav-actions">
              <li class="nds-nav-item nds-icon-only nds-pinned" id="nav-language">
                <a data-language-switch href="{LANGS[other]['path']}" class="nds-nav-link nds-btn nds-subtle nds-indicator nds-tooltip" data-tooltip-hover="500" title="{e(other_label)}" lang="{other_lang_attr}" hreflang="{other_lang_attr}"><i class="nds-icon nds-hgi-translation" aria-hidden="true"></i><span class="nds-label" data-hidden="sm md sr">{e(other_label)}</span></a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </nav>
  </header>
"""


def hero(lang):
    p = DATA["person"]
    ui = DATA["ui"]
    name = t(p["name_short"], lang)
    title = t(p["title"], lang)
    home_label = i18n(lang, "الرئيسية", "Home")
    share_label = i18n(lang, "مشاركة الصفحة", "Share Page")
    return f"""  <main>
    <section class="nds-hero-section nds-sub nds-flat" id="top">
      <nav class="nds-breadcrumb-nav" aria-label="{e(i18n(lang, 'مسار التنقل', 'Breadcrumb'))}" data-i18n-aria-label="breadcrumb.breadcrumb">
        <ol class="nds-breadcrumb">
          <li><a href="{LANGS[lang]['path']}">{e(home_label)}</a></li>
          <li class="nds-truncate" aria-current="page">{e(name)}</li>
        </ol>
      </nav>
      <div class="nds-section-wrapper">
        <div class="nds-section-image">
          <div class="nds-avatar nds-image-border alq-hero-avatar">
            <img src="/assets/img/portrait-480.webp" width="480" height="432" alt="{e(t(p['portrait_alt'], lang))}" fetchpriority="high">
          </div>
        </div>
        <div class="nds-section-head">
          <h1 class="nds-section-title">{e(name)}</h1>
          <p class="nds-section-description">{e(title)}. {e(t(p['tagline'], lang))}</p>
        </div>
        <div class="nds-section-action">
          <a class="nds-btn nds-primary" href="{e(CV_PATH)}" download="{e(CV_NAME)}">
            <i class="hgi hgi-stroke hgi-download-01" aria-hidden="true"></i>
            <span class="nds-label">{e(t(ui['download'], lang))}</span>
          </a>
          <a class="nds-btn nds-secondary-outline" href="#contact">
            <i class="nds-icon nds-hgi-mail-01" aria-hidden="true"></i>
            <span class="nds-label">{e(t(ui['contact_btn'], lang))}</span>
          </a>
          <div class="nds-share nds-dropmenu">
            <button class="nds-btn nds-secondary-outline nds-dropmenu-trigger" type="button" aria-label="{e(share_label)}" data-i18n-aria-label="share.share_page">
              <i class="nds-icon nds-hgi-share-01" aria-hidden="true"></i>
              <span class="nds-label" data-i18n="share.share_page">{e(share_label)}</span>
            </button>
            <div class="nds-dropmenu-menu" hidden>
              <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-x" type="button" aria-label="Share on X" data-i18n-aria-label="share.share_on_x">
                <i class="nds-icon nds-hgi-new-twitter" aria-hidden="true"></i>
                <span class="nds-label">X</span>
              </button>
              <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-linkedin" type="button" aria-label="Share on LinkedIn" data-i18n-aria-label="share.share_on_linkedin">
                <i class="nds-icon nds-hgi-linkedin-02" aria-hidden="true"></i>
                <span class="nds-label">LinkedIn</span>
              </button>
              <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-whatsapp" type="button" aria-label="Share on WhatsApp" data-i18n-aria-label="share.share_on_whatsapp">
                <i class="nds-icon nds-hgi-whatsapp" aria-hidden="true"></i>
                <span class="nds-label">WhatsApp</span>
              </button>
              <button class="nds-btn nds-subtle nds-dropmenu-item nds-share-copy" type="button" aria-label="{e(i18n(lang, 'نسخ الرابط', 'Copy Link'))}" data-i18n-aria-label="share.copy_link" data-copy-label data-no-auto-close>
                <i class="nds-icon nds-hgi-link-04" aria-hidden="true"></i>
                <span class="nds-label" data-i18n="share.copy_link">{e(i18n(lang, 'نسخ الرابط', 'Copy Link'))}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
"""


def section_head(title, description=""):
    desc = f'\n          <p class="nds-section-description">{e(description)}</p>' if description else ""
    return f"""        <div class="nds-section-head">
          <h2 class="nds-section-title">{e(title)}</h2>{desc}
        </div>"""


def about_block(lang):
    a = DATA["about"]
    facts = []
    icons = ["hgi-mosque-01", "hgi-calendar-03", "hgi-user-group", "hgi-book-open-02"]
    for i, fact in enumerate(DATA["hero_facts"]):
        icon = icons[i % len(icons)]
        facts.append(
            f"""              <div class="nds-definition-item nds-card nds-stroke">
                <dt>
                  <i class="hgi hgi-stroke {icon}" aria-hidden="true"></i>
                  <span class="nds-label">{e(t(fact['label'], lang))}</span>
                </dt>
                <dd>{e(fill_tokens(t(fact['value'], lang), lang))}</dd>
              </div>"""
        )
    tags = []
    for item in a["focus"]:
        tags.append(
            f"""              <span class="nds-tag nds-green nds-sm"><span class="nds-label">{e(t(item['title'], lang))}</span></span>"""
        )
    focus_notes = "".join(
        f"<p><strong>{e(t(item['title'], lang))}</strong> — {e(t(item['text'], lang))}</p>"
        for item in a["focus"]
    )
    return f"""            <div class="nds-section-wrapper" id="about">
{section_head(t(a['heading'], lang), t(DATA['person']['intro'], lang))}
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
{chr(10).join(tags)}
                  </div>
                </div>
              </div>
            </div>"""


def experience_block(lang):
    exp = DATA["experience"]
    items = exp["items"]
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
            f"""                        <div class="nds-stepper-step">
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
    return f"""            <div class="nds-section-wrapper" id="experience">
{section_head(t(exp['heading'], lang), t(exp['intro'], lang))}
              <div class="nds-section-body">
                <div class="nds-stepper nds-vertical nds-dot" data-current="{total}" data-total="{total}">
{chr(10).join(steps)}
                </div>
              </div>
            </div>"""


def community_block(lang):
    c = DATA["community"]
    cards = []
    for group in c["groups"]:
        lis = "".join(f"<li>{e(t(item, lang))}</li>" for item in group["items"])
        cards.append(
            f"""                <div class="nds-card nds-stroke alq-full">
                  <div class="nds-card-content">
                    <div class="nds-card-text">
                      <span class="nds-card-title">{e(t(group['title'], lang))}</span>
                      <ul>{lis}</ul>
                    </div>
                  </div>
                </div>"""
        )
    achievements = "".join(f"<li>{e(t(item, lang))}</li>" for item in c["achievements"])
    return f"""            <div class="nds-section-wrapper" id="community">
{section_head(t(c['heading'], lang))}
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
              </div>
            </div>"""


def skills_block(lang):
    s = DATA["skills"]
    groups = []
    for group in s["groups"]:
        tags = "".join(
            f'<span class="nds-tag nds-green nds-sm"><span class="nds-label">{e(t(tag, lang))}</span></span>'
            for tag in group["tags"]
        )
        groups.append(
            f"""                <div class="nds-card nds-stroke alq-full">
                  <div class="nds-card-content">
                    <div class="nds-card-text">
                      <span class="nds-card-title">{e(t(group['title'], lang))}</span>
                    </div>
                    <div class="nds-flex nds-wrap alq-tags">{tags}</div>
                  </div>
                </div>"""
        )
    return f"""            <div class="nds-section-wrapper" id="skills">
{section_head(t(s['heading'], lang), t(s['intro'], lang))}
              <div class="nds-section-body">
                <div class="nds-flex nds-col alq-stack">
{chr(10).join(groups)}
                </div>
              </div>
            </div>"""


def publications_block(lang):
    p = DATA["publications"]
    cards = []
    for item in p["items"]:
        cards.append(
            f"""                <div class="nds-card nds-stroke alq-full">
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
    return f"""            <div class="nds-section-wrapper" id="publications">
{section_head(t(p['heading'], lang), t(p['intro'], lang))}
              <div class="nds-section-body">
                <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
                </div>
              </div>
            </div>"""


def education_block(lang):
    edu = DATA["education"]
    cards = []
    for item in edu["items"]:
        period = t(item["period"], lang) if item.get("period") else ""
        meta = ""
        if period:
            meta = f"""                    <div class="nds-card-meta">
                      <div class="nds-card-tags">
                        <span class="nds-tag nds-green nds-rounded nds-sm"><span class="nds-label">{e(period)}</span></span>
                      </div>
                    </div>"""
        cards.append(
            f"""                <div class="nds-card nds-stroke nds-horizontal alq-full">
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
                    </div>
{meta}
                  </div>
                </div>"""
        )
    return f"""            <div class="nds-section-wrapper" id="education">
{section_head(t(edu['heading'], lang))}
              <div class="nds-section-body">
                <div class="nds-flex nds-col alq-stack">
{chr(10).join(cards)}
                </div>
              </div>
            </div>"""


def training_block(lang):
    tr = DATA["training"]
    lis = "".join(f"<li>{e(t(item, lang))}</li>" for item in tr["items"])
    return f"""            <div class="nds-section-wrapper" id="training">
{section_head(t(tr['heading'], lang))}
              <div class="nds-section-body">
                <div class="nds-card nds-stroke alq-full">
                  <div class="nds-card-content">
                    <div class="nds-prose">
                      <ul>{lis}</ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>"""


def contact_block(lang):
    c = DATA["contact"]
    ui = DATA["ui"]
    return f"""            <div class="nds-section-wrapper" id="contact">
{section_head(t(c['heading'], lang), t(c['text'], lang))}
              <div class="nds-section-action">
                <a class="nds-btn nds-primary" href="mailto:{e(EMAIL)}">
                  <i class="nds-icon nds-hgi-mail-01" aria-hidden="true"></i>
                  <span class="nds-label">{e(t(ui['email_btn'], lang))}</span>
                </a>
                <a class="nds-btn nds-secondary-outline" href="{e(CV_PATH)}" download="{e(CV_NAME)}">
                  <i class="hgi hgi-stroke hgi-download-01" aria-hidden="true"></i>
                  <span class="nds-label">{e(t(ui['download'], lang))}</span>
                </a>
              </div>
              <div class="nds-section-body">
                <dl class="nds-definition-list nds-grid alq-facts">
                  <div class="nds-definition-item nds-card nds-stroke">
                    <dt>
                      <i class="hgi hgi-stroke hgi-mail-01" aria-hidden="true"></i>
                      <span class="nds-label">{e(t(c['email_label'], lang))}</span>
                    </dt>
                    <dd><a class="nds-link alq-text-link" href="mailto:{e(EMAIL)}"><bdi dir="ltr">{e(EMAIL)}</bdi></a></dd>
                  </div>
                </dl>
              </div>
            </div>"""


def content_layout(lang):
    name = t(DATA["person"]["name_short"], lang)
    toc_label = t(DATA["ui"]["toc_title"], lang)
    toc_links = "\n".join(
        f'<li><a href="#{n["id"]}" class="nds-btn nds-subtle nds-indicator">'
        f'<span class="nds-label nds-truncate">{e(t(n["label"], lang))}</span></a></li>'
        for n in DATA["nav"]
    )
    return f"""    <div class="nds-content-layout nds-has-sideinfo">
      <div class="nds-content" id="main-content">
        <section id="profile" class="nds-content-section nds-sideinfo-section">
          <div class="nds-section-body">
            <aside class="nds-sideinfo nds-sticky nds-top" aria-label="{e(i18n(lang, 'في هذه الصفحة', 'On this page'))}" data-i18n-aria-label="toc.on_this_page">
              <nav class="nds-toc alq-toc" aria-label="{e(t(DATA['ui']['index_aria'], lang))}" data-i18n-aria-label="toc.table_of_contents">
                <div class="nds-toc-head">
                  <span class="nds-label" data-i18n="toc.on_this_page">{e(i18n(lang, 'في هذه الصفحة', 'On this page'))}</span>
                  <h2 class="nds-toc-title nds-truncate">{e(name)}</h2>
                </div>
                <div class="nds-drawer nds-lined">
                  <ul class="nds-drawer-list">{toc_links}</ul>
                </div>
              </nav>
            </aside>
            <div class="nds-info-content">
{about_block(lang)}
{experience_block(lang)}
{community_block(lang)}
{skills_block(lang)}
{publications_block(lang)}
{education_block(lang)}
{training_block(lang)}
{contact_block(lang)}
            </div>
          </div>
        </section>
        <section class="nds-last-edit nds-content-section">
          {e(t(DATA['ui']['updated_note'], lang))}
        </section>
      </div>
    </div>
  </main>
"""


def footer(lang, not_found=False):
    ui = DATA["ui"]
    name = t(DATA["person"]["name_short"], lang)
    nav_links = []
    for n in DATA["nav"]:
        nav_links.append(
            f"""        <li>
          <a class="nds-link nds-footer-link alq-text-link" href="{LANGS[lang]['path'] if not_found else ''}#{n['id']}">
            <span class="nds-label">{e(t(n['label'], lang))}</span>
          </a>
        </li>"""
        )
    sections_heading = i18n(lang, "أقسام الصفحة", "Page sections")
    contact_heading = t(DATA["contact"]["heading"], lang)
    rights = t(ui["footer_rights"], lang)
    aria = i18n(lang, "تذييل الموقع", "Site Footer")
    return f"""  <footer class="nds-footer nds-content-wrapper nds-brand" aria-label="{e(aria)}" data-i18n-aria-label="footer.site_footer">
    <nav class="nds-footer-content" aria-label="{e(i18n(lang, 'تنقل التذييل', 'Footer navigation'))}" data-i18n-aria-label="footer.footer_navigation">
      <div class="nds-footer-column">
        <span class="nds-footer-heading" id="footer-col-1">{e(sections_heading)}</span>
        <ul class="nds-footer-list" aria-labelledby="footer-col-1">
{chr(10).join(nav_links)}
        </ul>
      </div>
      <div class="nds-footer-column">
        <span class="nds-footer-heading" id="footer-col-2">{e(contact_heading)}</span>
        <ul class="nds-footer-list" aria-labelledby="footer-col-2">
          <li>
            <a class="nds-link nds-footer-link alq-text-link" href="mailto:{e(EMAIL)}">
              <i class="nds-icon nds-hgi-mail-01" aria-hidden="true"></i>
              <span class="nds-label"><bdi dir="ltr">{e(EMAIL)}</bdi></span>
            </a>
          </li>
          <li>
            <a class="nds-link nds-footer-link alq-text-link" href="{e(CV_PATH)}" download="{e(CV_NAME)}">
              <i class="hgi hgi-stroke hgi-download-01" aria-hidden="true"></i>
              <span class="nds-label">{e(t(ui['download'], lang))}</span>
            </a>
          </li>
        </ul>
      </div>
    </nav>
    <div class="nds-footer-bottom">
      <div class="nds-footer-meta">
        <div class="nds-footer-legal">
          <div class="nds-footer-copyright">
            <span>{e(name)} &copy; {YEAR_FALLBACK}. {e(rights)}</span>
          </div>
        </div>
      </div>
    </div>
  </footer>
  <script defer src="/assets/js/nds-main.min.js?ver={ASSET_VER}"></script>
  <script type="module" src="/assets/js/site.js"></script>
</body>
</html>
"""


def page(lang):
    seo = DATA["seo"][lang]
    return (
        head(lang, seo["title"], seo["description"])
        + header(lang)
        + hero(lang)
        + content_layout(lang)
        + footer(lang)
    )


def page_404():
    seo_title = "404 | الصفحة غير موجودة"
    extra = '<meta name="robots" content="noindex">'
    head_html = head("ar", seo_title, "الصفحة غير موجودة", extra_meta=extra, not_found=True)
    main_html = f"""  <main>
    <div class="nds-content-layout">
      <div class="nds-content" id="main-content">
        <section id="not-found" class="nds-content-section nds-status-section">
          <div class="nds-section-wrapper">
            <div class="nds-section-image">
              <img src="/assets/img/404.svg" width="458" height="324" alt="">
            </div>
            <div class="nds-section-head">
              <h1 class="nds-section-title">الصفحة غير موجودة</h1>
              <p class="nds-section-description">الرابط الذي فتحته غير موجود أو تم نقله.</p>
            </div>
            <div class="nds-section-action">
              <a href="/" class="nds-btn nds-primary"><span class="nds-label">الصفحة الرئيسية</span></a>
              <a href="/en/" class="nds-btn nds-secondary-outline" lang="en"><span class="nds-label">Home (English)</span></a>
            </div>
          </div>
        </section>
      </div>
    </div>
  </main>
"""
    return head_html + header("ar", not_found=True) + main_html + footer("ar", not_found=True)


def sitemap():
    urls = []
    for lang, meta in LANGS.items():
        loc = SITE_URL + meta["path"]
        alts = chr(10).join(
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


def main():
    validate_config()
    validate_nav_counts()
    (ROOT / "index.html").write_text(page("ar"), encoding="utf-8")
    en_dir = ROOT / "en"
    en_dir.mkdir(exist_ok=True)
    (en_dir / "index.html").write_text(page("en"), encoding="utf-8")
    (ROOT / "404.html").write_text(page_404(), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    for name in ("index.html", "en/index.html", "404.html"):
        path = ROOT / name
        path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    write_csp([(ROOT / name).read_text(encoding="utf-8")
               for name in ("index.html", "en/index.html", "404.html")])
    print("Built index.html, en/index.html, 404.html, sitemap.xml and CSP hashes")


if __name__ == "__main__":
    main()
