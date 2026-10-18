#!/usr/bin/env python3
"""Browser regression suite for the current NDS static pages.

Build/package, start tools/serve.py, then run this script with its base URL.
Requires requirements-test.txt and a Playwright browser (BROWSER defaults to
chromium; also firefox/webkit). Optional <ENGINE>_EXECUTABLE_PATH supports a
preinstalled browser; AXE_JS_PATH must point to axe-core >= 4.10.
Results/screenshots go to ignored test-results/ (or TEST_RESULTS_DIR), not dist/.
Playwright WebKit is not a real Safari or manual VoiceOver test.
"""
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8000'
ENGINE = os.environ.get('BROWSER', 'chromium')
if ENGINE not in ('chromium', 'firefox', 'webkit'):
    raise SystemExit('BROWSER must be chromium, firefox or webkit')
OUT = Path(os.environ.get('TEST_RESULTS_DIR', str(ROOT / 'test-results')))
OUT.mkdir(parents=True, exist_ok=True)
AXE = Path(os.environ.get('AXE_JS_PATH', str(ROOT / 'node_modules/axe-core/axe.min.js')))
if not AXE.is_file():
    raise SystemExit('axe-core is required: npm ci (or set AXE_JS_PATH)')
report = {'checks': [], 'failures': 0, 'base': BASE, 'widths': [360, 375, 430, 768, 861, 900, 1024, 1100, 1366, 1440, 1920]}


def check(name, ok, detail=''):
    report['checks'].append({'name': name, 'ok': bool(ok), 'detail': detail})
    report['failures'] += int(not ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f' [{detail}]' if detail else ''), flush=True)
    if not ok and os.environ.get('GITHUB_ACTIONS') == 'true':
        annotation = (name + ': ' + detail).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=Browser regression::' + annotation, flush=True)


def ready(page, path):
    response = page.goto(BASE + path, wait_until='networkidle')
    page.wait_for_function("document.documentElement.hasAttribute('data-nds-loaded')")
    page.evaluate('document.fonts.ready')
    return response


try:
    with sync_playwright() as p:
        executable = os.environ.get(ENGINE.upper() + '_EXECUTABLE_PATH')
        options = {'executable_path': executable} if executable else {}
        browser = getattr(p, ENGINE).launch(**options)
        report['engine'] = ENGINE
        report['browser'] = browser.version
        for lang, path in [('ar', '/'), ('en', '/en/'), ('404', '/missing/audit/')]:
            widths = report['widths'] if lang != '404' else [375, 1366]
            for width in widths:
                ctx = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                page = ctx.new_page()
                errors, bad_responses, external, warnings = [], [], [], []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and not (lang == '404' and m.text == 'Failed to load resource: the server responded with a status of 404 (Not Found)' and m.location.get('url') == BASE + path) else warnings.append(m.text) if m.type == 'warning' else None)
                page.on('response', lambda r: bad_responses.append(f'{r.status} {r.url}') if r.status >= 400 and r.request.resource_type != 'document' else None)
                page.on('request', lambda r: external.append(r.url) if urlsplit(r.url).netloc != urlsplit(BASE).netloc else None)
                response = ready(page, path)
                label = f'{lang}/{width}'
                check(label + ' status', response.status == (404 if lang == '404' else 200))
                check(label + ' viewport and overflow', page.evaluate('innerWidth') == width and page.evaluate('document.documentElement.scrollWidth - innerWidth') <= 1)
                check(label + ' visible main content', page.locator('#main-content').is_visible() and page.locator('h1').is_visible())
                check(label + ' images loaded', page.evaluate('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)'))
                check(label + ' no browser/CSP/network errors', not errors and not bad_responses and not external, json.dumps(errors + bad_responses + external)[:1500])
                # Audit returns a Promise; await it, not a serialized empty Promise.
                audit = page.evaluate('async () => await NDS.Init.audit()')
                check(label + ' NDS audit', not warnings and not audit, json.dumps({'audit': audit, 'warnings': warnings}, ensure_ascii=False)[:1600])
                if lang != '404':
                    links = page.locator('.nds-toc a')
                    check(label + ' eight stable TOC destinations', links.count() == 8 and page.evaluate("Array.from(document.querySelectorAll('.nds-toc a')).every(a=>document.getElementById(a.hash.slice(1)))"))
                    check(label + ' all content groups retained', page.locator('.nds-stepper-step').count() == 5 and page.locator('#training li').count() == 10 and page.locator('#education .nds-card').count() == 2)
                if width in [375, 1366]:
                    page.screenshot(path=str(OUT / f'{lang}-{width}-top.png'))
                    page.screenshot(path=str(OUT / f'{lang}-{width}-full.png'), full_page=True)
                    # Browser instrumentation via evaluate does not relax production CSP.
                    page.evaluate(AXE.read_text(encoding='utf-8'))
                    result = page.evaluate("""async () => { const r = await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}); return {version:axe.version,violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.html)}))}; }""")
                    report['axe_version'] = result['version']
                    check(label + ' axe WCAG 2.2 AA/best practice', not result['violations'], json.dumps(result['violations'], ensure_ascii=False))
                    page.keyboard.press('Tab')
                    check(label + ' skip link keyboard focus', page.locator('.nds-skip-link').evaluate('(e)=>e===document.activeElement'))
                    focus = page.locator('.nds-skip-link').evaluate('(e)=>{const s=getComputedStyle(e);return {outline:s.outlineStyle,shadow:s.boxShadow,y:e.getBoundingClientRect().y}}')
                    check(label + ' keyboard focus visibly styled', focus['y'] >= 0 and (focus['outline'] != 'none' or focus['shadow'] != 'none'), json.dumps(focus))
                    small = page.evaluate("""() => Array.from(document.querySelectorAll('a,button')).filter(e=>!e.matches('.nds-skip-link')).filter(e=>{const r=e.getBoundingClientRect();return r.width>0 && r.height>0 && getComputedStyle(e).visibility==='visible' && (r.width<24 || r.height<24)}).map(e=>e.textContent.trim())""")
                    check(label + ' visible targets at least 24px', not small, json.dumps(small, ensure_ascii=False))
                    page.keyboard.press('Enter')
                    check(label + ' skip link reaches main', page.evaluate("location.hash === '#main-content'"))
                    check(label + ' HGI glyph stylesheet', page.evaluate("getComputedStyle(document.querySelector('.hgi'),'::before').content") not in ['none', 'normal', '""']) if lang != '404' else None
                ctx.close()

        for lang, path, other in [('ar', '/', '/en/'), ('en', '/en/', '/')]:
            for width in [375, 1366]:
                ctx = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                page = ctx.new_page()
                ready(page, path)
                if width == 375:
                    toggle = page.locator('.nds-nav-toggler button')
                    toggle.click()
                    check(lang + ' mobile menu opens', toggle.get_attribute('aria-expanded') == 'true')
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(400)
                    check(lang + ' Escape closes mobile menu', toggle.get_attribute('aria-expanded') == 'false')
                for section in ['about', 'experience', 'community', 'skills', 'publications', 'education', 'training', 'contact']:
                    page.locator(f'.nds-toc a[href="#{section}"]').click()
                    page.wait_for_timeout(100)
                    check(f'{lang}/{width} TOC {section}', page.evaluate('location.hash') == '#' + section and page.locator('#' + section).bounding_box()['y'] >= -2)
                page.locator('[data-language-switch]').click()
                page.wait_for_load_state('networkidle')
                check(f'{lang}/{width} language keeps section', page.url == BASE + other + '#contact', page.url)
                page.go_back(wait_until='networkidle')
                check(f'{lang}/{width} browser back', urlsplit(page.url).path == path)
                page.go_forward(wait_until='networkidle')
                check(f'{lang}/{width} browser forward', page.url == BASE + other + '#contact')
                ready(page, path)
                trigger = page.locator('.nds-share .nds-dropmenu-trigger')
                trigger.click()
                check(f'{lang}/{width} share opens', page.locator('.nds-share .nds-dropmenu-menu').is_visible())
                # Stub only external popup navigation: verify encoded destination without contacting third parties.
                page.evaluate('window.open=(url)=>{window.__shareUrl=url; return null}')
                page.locator('.nds-share-x').click()
                check(f'{lang}/{width} X destination', page.evaluate("window.__shareUrl.startsWith('https://x.com/intent/tweet?url=')"))
                trigger.click()
                if not page.locator('.nds-share-copy').is_visible():
                    trigger.click()
                page.evaluate('window.__copied=null; NDS.Copy.writeText=async t=>{window.__copied=t;return true}')
                page.locator('.nds-share-copy').click()
                check(f'{lang}/{width} copy delegates current URL', page.evaluate('window.__copied===location.href'))
                page.keyboard.press('Escape')
                with page.expect_download() as info:
                    page.locator('.nds-hero-section a[download]').click()
                check(f'{lang}/{width} CV download', info.value.suggested_filename == 'abdulaziz-al-qaeed-cv.pdf')
                page.emulate_media(media='print')
                check(f'{lang}/{width} print content visible', all(page.locator('#' + section).is_visible() for section in ['about','experience','contact']))
                ctx.close()

        # No JavaScript must retain reading, section navigation, PDF and the language switch.
        for path in ['/', '/en/', '/missing/audit/']:
            for width in [375, 1366]:
                ctx = browser.new_context(java_script_enabled=False, viewport={'width': width, 'height': 900})
                page = ctx.new_page()
                page.goto(BASE + path, wait_until='networkidle')
                check(f'no-JS {path}/{width} content and language visible', page.locator('h1').is_visible() and page.locator('[data-language-switch]:visible').count() == 1)
                check(f'no-JS {path}/{width} sections visible', path.startswith('/missing') or all(page.locator('#'+s).is_visible() for s in ['about','experience','community','skills','publications','education','training','contact']))
                readable = page.evaluate("""() => Array.from(document.querySelectorAll('.nds-card-title,.nds-card-description,.nds-definition-list dt,.nds-definition-list dd,.nds-card .nds-label')).every(e=>getComputedStyle(e).color!=='rgba(0, 0, 0, 0)' && getComputedStyle(e).visibility==='visible')""")
                check(f'no-JS {path}/{width} card/fact text not skeleton-transparent', readable)
                check(f'no-JS {path}/{width} no overflow', page.evaluate('document.documentElement.scrollWidth-innerWidth') <= 1)
                check(f'no-JS {path}/{width} no inert share button', page.locator('.nds-share:visible').count() == 0)
                page.screenshot(path=str(OUT / f'no-js-{width}-{path.replace("/", "_")}.png'))
                ctx.close()

        # Stored dark preference, reduced motion and enlarged text are regression checks, not manual AT certification.
        for path in ['/', '/en/']:
            ctx = browser.new_context(viewport={'width': 375, 'height': 900}, reduced_motion='reduce')
            page = ctx.new_page()
            page.add_init_script("localStorage.setItem('nds-theme','dark')")
            ready(page, path)
            check(path + ' dark preference restored', page.evaluate("document.documentElement.getAttribute('data-theme').includes('dark')"))
            page.evaluate(AXE.read_text())
            result = page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2aa','wcag21aa','wcag22aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.html)}))")
            check(path + ' dark axe AA', not result, json.dumps(result, ensure_ascii=False))
            page.screenshot(path=str(OUT / ('dark-ar.png' if path == '/' else 'dark-en.png')))
            page.evaluate("document.documentElement.style.fontSize='200%'")
            check(path + ' 200% text no horizontal overflow', page.evaluate('document.documentElement.scrollWidth-innerWidth') <= 1)
            ctx.close()

        # Block a real lazy network dependency: translated source content remains readable.
        ctx = browser.new_context()
        ctx.route('**/assets/i18n/**', lambda route: route.abort())
        page = ctx.new_page()
        ready(page, '/')
        check('translation request failure preserves authored biography', page.locator('#about').is_visible() and 'الشيخ' in page.locator('#about').inner_text())
        ctx.close()
        browser.close()

    with urlopen(BASE + '/assets/docs/abdulaziz-al-qaeed-cv.pdf') as response:
        data = response.read()
    pdf = PdfReader(io.BytesIO(data))
    check('existing CV A4 selectable text', abs(float(pdf.pages[0].mediabox.width)-595)<2 and sum(len(p.extract_text() or '') for p in pdf.pages)>2000, f'{len(pdf.pages)} pages, {len(data)} bytes')
except Exception as exc:
    check('suite completed without harness exception', False, f'{type(exc).__name__}: {exc}')
finally:
    (OUT / 'browser-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = f"{ENGINE}: {len(report['checks'])-report['failures']}/{len(report['checks'])} passed; browser {report.get('browser', 'not launched')}"
    print('\n' + summary)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print('::notice title=Browser verification::' + summary)
sys.exit(1 if report['failures'] else 0)
