#!/usr/bin/env python3
"""
Generates the static pages from content/content.json.

  python3 tools/build.py

Generated root outputs (committed for review and root-level local preview):
  index.html          Arabic (default, RTL)
  en/index.html       English (LTR)
  404.html            Not-found page
  sitemap.xml         With hreflang alternates

For Cloudflare Pages, run tools/package.py after this script and deploy dist/. That
allowlisted static output excludes repository documentation, tests, and source data.

To add a third language: add an entry to LANGS below and a matching key
("xx") next to every "ar"/"en" value in content/content.json.
"""
import html
import json
import pathlib

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

ICON = {
    "download": '<path d="M12 3v12m0 0l-4.5-4.5M12 15l4.5-4.5M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3"/>',
    "mail": '<path d="M3.5 6.5h17v11h-17z"/><path d="M3.5 7l8.5 6.5L20.5 7"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def e(s):
    return html.escape(str(s), quote=True)


def t(value, lang):
    """Return the text for a language. Accepts {'ar':..,'en':..} or a plain string."""
    if isinstance(value, dict):
        return value.get(lang) or value.get(DEFAULT) or ""
    return value


def icon(name, cls=""):
    c = f' class="ico {cls}"' if cls else ' class="ico"'
    return (
        f'<svg{c} viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false" '
        f'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{ICON[name]}</svg>"
    )


def other_lang(lang):
    return "en" if lang == "ar" else "ar"


def page_url(lang):
    return SITE_URL + LANGS[lang]["path"]


def head(lang):
    L = LANGS[lang]
    seo = DATA["seo"][lang]
    person = DATA["person"]
    name = t(person["name_short"], lang)
    alt_links = "\n".join(
        f'  <link rel="alternate" hreflang="{k}" href="{e(SITE_URL + v["path"])}">' for k, v in LANGS.items()
    )
    preload_fonts = (
        ["/assets/fonts/ibm-plex-sans-arabic-arabic-400-normal.woff2",
         "/assets/fonts/ibm-plex-sans-arabic-arabic-700-normal.woff2",
         "/assets/fonts/noto-naskh-arabic-arabic-400-normal.woff2"]
        if lang == "ar"
        else ["/assets/fonts/satoshi-700.woff2",
              "/assets/fonts/ibm-plex-sans-arabic-latin-400-normal.woff2"]
    )
    preload = "\n  ".join(
        f'<link rel="preload" href="{u}" as="font" type="font/woff2" crossorigin>' for u in preload_fonts
    )
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": t(person["name_full"], lang),
        "alternateName": [DATA["person"]["name_short"]["ar"], DATA["person"]["name_short"]["en"]],
        "jobTitle": t(person["title"], lang),
        "description": seo["description"],
        "email": f"mailto:{EMAIL}",
        "url": page_url(lang),
        "image": SITE_URL + "/assets/img/portrait.jpg",
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Imam Muhammad ibn Saud Islamic University"},
        "inLanguage": L["html_lang"],
    }
    return f"""<!DOCTYPE html>
<html lang="{L['html_lang']}" dir="{L['dir']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(seo['title'])}</title>
  <meta name="description" content="{e(seo['description'])}">
  <meta name="theme-color" content="#0e5a49">
  <link rel="canonical" href="{e(page_url(lang))}">
  <link rel="alternate" hreflang="x-default" href="{e(SITE_URL + '/')}">
{alt_links}
  <meta property="og:type" content="profile">
  <meta property="og:site_name" content="{e(name)}">
  <meta property="og:title" content="{e(seo['title'])}">
  <meta property="og:description" content="{e(seo['description'])}">
  <meta property="og:url" content="{e(page_url(lang))}">
  <meta property="og:image" content="{e(SITE_URL + '/assets/img/portrait.jpg')}">
  <meta property="og:image:alt" content="{e(t(person['portrait_alt'], lang))}">
  <meta property="og:locale" content="{L['locale']}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
  {preload}
  <link rel="preload" as="image" href="/assets/img/portrait.webp" imagesrcset="/assets/img/portrait-480.webp 480w, /assets/img/portrait.webp 950w" imagesizes="(max-width: 1024px) 90vw, 500px" type="image/webp">
  <link rel="stylesheet" href="/assets/css/styles.css">
  <script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False, indent=2)}</script>
  <script src="/assets/js/main.js" defer></script>
</head>
"""


def header(lang):
    ui = DATA["ui"]
    other = other_lang(lang)
    links = "\n".join(
        f'        <li><a href="#{n["id"]}">{e(t(n["label"], lang))}</a></li>' for n in DATA["nav"]
    )
    return f"""<body>
<a class="skip-link" href="#main">{e(t(ui['skip'], lang))}</a>
<header class="site-header">
  <div class="wrap header-inner">
    <div class="brand-wrap">
      <span class="monogram" aria-hidden="true">{'ع ق' if lang == 'ar' else 'AQ'}</span>
      <a class="brand" href="{LANGS[lang]['path']}">{e(t(DATA['person']['name_short'], lang))}</a>
    </div>
    <nav class="primary-nav" aria-label="{'التنقل الرئيسي' if lang == 'ar' else 'Primary navigation'}">
      <ul>
{links}
      </ul>
    </nav>
    <a class="lang-switch" href="{LANGS[other]['path']}" hreflang="{LANGS[other]['html_lang']}" lang="{LANGS[other]['html_lang']}">{e(t(ui['switch_label'], lang))}</a>
  </div>
</header>
"""


def hero(lang):
    p = DATA["person"]
    ui = DATA["ui"]
    return f"""<main id="main">
  <section class="hero" id="top" aria-labelledby="hero-title">
    <div class="wrap hero-grid">
      <div class="hero-copy">
        <p class="eyebrow">{e(t(p['title'], lang))}</p>
        <h1 id="hero-title">{e(t(p['name_short'], lang))}</h1>
        <p class="fullname">{e(t(p['name_full'], lang))}</p>
        <p class="tagline">{e(t(p['tagline'], lang))}</p>
        <p class="intro">{e(t(p['intro'], lang))}</p>
        <div class="actions">
          <a class="btn btn-primary" href="{CV_PATH}" download="{CV_NAME}">{icon('download')}<span>{e(t(ui['download'], lang))}</span></a>
          <a class="btn btn-ghost" href="#contact">{e(t(ui['contact_btn'], lang))}</a>
        </div>
      </div>
      <figure class="hero-media">
        <picture>
          <source type="image/webp" srcset="/assets/img/portrait-480.webp 480w, /assets/img/portrait.webp 950w" sizes="(max-width: 1024px) 90vw, 500px">
          <img src="/assets/img/portrait.jpg" width="950" height="855" fetchpriority="high"
               alt="{e(t(p['portrait_alt'], lang))}">
        </picture>
      </figure>
    </div>
  </section>
"""


def about(lang):
    a = DATA["about"]
    cards = "\n".join(
        f"""        <article class="focus-card reveal">
          <h3>{e(t(f['title'], lang))}</h3>
          <p>{e(t(f['text'], lang))}</p>
        </article>"""
        for f in a["focus"]
    )
    return f"""
  <section class="section" id="about" aria-labelledby="about-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">01</p>
        <h2 id="about-title">{e(t(a['heading'], lang))}</h2>
      </header>
      <p class="lead reveal">{e(t(a['body'], lang))}</p>
      <h3 class="sub-heading reveal">{e(t(a['focus_heading'], lang))}</h3>
      <div class="bento">
{cards}
      </div>
    </div>
  </section>
"""


def experience(lang):
    x = DATA["experience"]
    items = []
    for it in x["items"]:
        note = f'<p class="note">{e(t(it["note"], lang))}</p>' if it.get("note") else ""
        items.append(
            f"""        <li class="tl-item reveal">
          <span class="tl-period">{e(t(it['period'], lang))}</span>
          <div class="tl-body">
            <h3>{e(t(it['role'], lang))}</h3>
            <p class="org">{e(t(it['org'], lang))}</p>
            {note}
          </div>
        </li>"""
        )
    return f"""
  <section class="section section-tint" id="experience" aria-labelledby="experience-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">02</p>
        <h2 id="experience-title">{e(t(x['heading'], lang))}</h2>
        <p class="section-intro">{e(t(x['intro'], lang))}</p>
      </header>
      <ol class="timeline">
{chr(10).join(items)}
      </ol>
    </div>
  </section>
"""


def community(lang):
    c = DATA["community"]
    groups = []
    for g in c["groups"]:
        lis = "\n".join(f'            <li>{e(t(i, lang))}</li>' for i in g["items"])
        groups.append(
            f"""        <article class="card reveal">
          <h3>{e(t(g['title'], lang))}</h3>
          <ul class="list">
{lis}
          </ul>
        </article>"""
        )
    ach = "\n".join(f'          <p>{e(t(a, lang))}</p>' for a in c["achievements"])
    return f"""
  <section class="section" id="community" aria-labelledby="community-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">03</p>
        <h2 id="community-title">{e(t(c['heading'], lang))}</h2>
      </header>
      <div class="cards-2">
{chr(10).join(groups)}
      </div>
      <div class="callout reveal">
        <h3>{e(t(c['achievements_heading'], lang))}</h3>
{ach}
      </div>
    </div>
  </section>
"""


def skills(lang):
    s = DATA["skills"]
    groups = []
    for g in s["groups"]:
        tags = "\n".join(f'            <li>{e(t(tg, lang))}</li>' for tg in g["tags"])
        groups.append(
            f"""        <article class="card reveal">
          <h3>{e(t(g['title'], lang))}</h3>
          <ul class="tags">
{tags}
          </ul>
        </article>"""
        )
    return f"""
  <section class="section section-tint" id="skills" aria-labelledby="skills-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">04</p>
        <h2 id="skills-title">{e(t(s['heading'], lang))}</h2>
        <p class="section-intro">{e(t(s['intro'], lang))}</p>
      </header>
      <div class="cards-2">
{chr(10).join(groups)}
      </div>
    </div>
  </section>
"""


def publications(lang):
    p = DATA["publications"]
    items = "\n".join(
        f"""        <li class="pub reveal"><span class="pub-no">{i:02d}</span><span>{e(t(it, lang))}</span></li>"""
        for i, it in enumerate(p["items"], start=1)
    )
    return f"""
  <section class="section" id="publications" aria-labelledby="publications-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">05</p>
        <h2 id="publications-title">{e(t(p['heading'], lang))}</h2>
        <p class="section-intro">{e(t(p['intro'], lang))}</p>
      </header>
      <ol class="pub-grid">
{items}
      </ol>
    </div>
  </section>
"""


def education(lang):
    ed = DATA["education"]
    items = []
    for it in ed["items"]:
        period = f'<p class="period">{e(t(it["period"], lang))}</p>' if it.get("period") else ""
        items.append(
            f"""        <article class="card reveal">
          <h3>{e(t(it['title'], lang))}</h3>
          <p class="org">{e(t(it['org'], lang))}</p>
          {period}
        </article>"""
        )
    return f"""
  <section class="section section-tint" id="education" aria-labelledby="education-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">06</p>
        <h2 id="education-title">{e(t(ed['heading'], lang))}</h2>
      </header>
      <div class="cards-2">
{chr(10).join(items)}
      </div>
    </div>
  </section>
"""


def training(lang):
    tr = DATA["training"]
    items = "\n".join(
        f'        <li class="reveal">{icon("check", "ico-check")}<span>{e(t(i, lang))}</span></li>'
        for i in tr["items"]
    )
    return f"""
  <section class="section" id="training" aria-labelledby="training-title">
    <div class="wrap">
      <header class="section-head reveal">
        <p class="kicker">07</p>
        <h2 id="training-title">{e(t(tr['heading'], lang))}</h2>
      </header>
      <ul class="cert-list">
{items}
      </ul>
    </div>
  </section>
"""


def contact(lang):
    c = DATA["contact"]
    ui = DATA["ui"]
    return f"""
<section class="contact" id="contact" aria-labelledby="contact-title">
  <div class="wrap contact-inner reveal">
    <div>
      <p class="kicker kicker-light">08</p>
      <h2 id="contact-title">{e(t(c['heading'], lang))}</h2>
      <p>{e(t(c['text'], lang))}</p>
    </div>
    <div class="contact-actions">
      <a class="btn btn-light" href="mailto:{e(EMAIL)}">{icon('mail')}<span>{e(t(ui['email_btn'], lang))}</span></a>
      <p class="email-line"><span>{e(t(c['email_label'], lang))}:</span> <a href="mailto:{e(EMAIL)}" dir="ltr">{e(EMAIL)}</a></p>
    </div>
  </div>
</section>
</main>
"""


def footer(lang):
    ui = DATA["ui"]
    links = "\n".join(
        f'      <a href="#{n["id"]}">{e(t(n["label"], lang))}</a>' for n in DATA["nav"]
    )
    return f"""<footer class="site-footer">
  <div class="wrap footer-inner">
    <div>
      <p class="footer-name">{e(t(DATA['person']['name_short'], lang))}</p>
      <p class="footer-note">{e(t(ui['cv_note'], lang))}</p>
    </div>
    <nav class="footer-nav" aria-label="{'روابط الصفحة' if lang == 'ar' else 'Page links'}">
{links}
    </nav>
    <p class="copy">© <span data-year>{YEAR_FALLBACK}</span> {e(t(ui['footer_rights'], lang))}</p>
  </div>
</footer>
</body>
</html>
"""


def render(lang):
    return head(lang) + header(lang) + hero(lang) + about(lang) + experience(lang) + community(lang) + \
        skills(lang) + publications(lang) + education(lang) + training(lang) + contact(lang) + footer(lang)


def render_404():
    ar_title = "الصفحة غير موجودة"
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>404 | {e(ar_title)}</title>
  <link rel="stylesheet" href="/assets/css/styles.css">
</head>
<body class="page-404">
  <main class="notfound wrap" id="main">
    <p class="kicker">404</p>
    <h1>{ar_title}</h1>
    <p>الرابط الذي فتحته غير موجود أو تم نقله.</p>
    <p class="en" lang="en" dir="ltr">The page you requested does not exist or has moved.</p>
    <div class="actions">
      <a class="btn btn-primary" href="/">الصفحة الرئيسية</a>
      <a class="btn btn-ghost" href="/en/" lang="en">Home (English)</a>
    </div>
  </main>
</body>
</html>
"""


def render_sitemap():
    urls = []
    for lang in LANGS:
        alts = "\n".join(
            f'    <xhtml:link rel="alternate" hreflang="{k}" href="{e(SITE_URL + v["path"])}"/>'
            for k, v in LANGS.items()
        )
        urls.append(
            f"  <url>\n    <loc>{e(page_url(lang))}</loc>\n{alts}\n"
            f"    <xhtml:link rel=\"alternate\" hreflang=\"x-default\" href=\"{e(SITE_URL + '/')}\"/>\n  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n"
    )


def main():
    import re

    def clean(s):
        return re.sub(r"[ \t]+$", "", s, flags=re.M)

    (ROOT / "index.html").write_text(clean(render("ar")), encoding="utf-8")
    (ROOT / "en").mkdir(exist_ok=True)
    (ROOT / "en" / "index.html").write_text(clean(render("en")), encoding="utf-8")
    (ROOT / "404.html").write_text(clean(render_404()), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(clean(render_sitemap()), encoding="utf-8")
    print("built: index.html, en/index.html, 404.html, sitemap.xml")


if __name__ == "__main__":
    main()
