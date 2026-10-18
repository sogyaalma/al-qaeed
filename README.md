# الشيخ عبدالعزيز القعيد — السيرة التعريفية
# Sheikh Abdulaziz Al-Qaeed — Biographical Profile

موقع شخصي ثابت بالعربية **RTL** والإنجليزية **LTR**. مصدر المحتوى واحد، ولا يحتاج إلى خادم تطبيقات أو قاعدة بيانات أو متغيرات سرية.
A bilingual, self-hosted static biography, generated from JSON with Python's standard library and deployed as files on Cloudflare Pages.

**الحالة:** أُصلحت عيوب مؤكدة واختُبرت حزمة الموقع محليًا؛ لم يُنشر للإنتاج من جولة التدقيق. مراجعة المحتوى وحقوق الأصول وإعدادات Cloudflare مطلوبة قبل الاعتماد. النتائج والقيود في [تقرير التدقيق](docs/AUDIT-2026-10-18.md) و[ملحق استكمال المتبقي](docs/CONTINUATION-2026-10-18.md).

## المزايا / Features

- `/` بالعربية، `/en/` بالإنجليزية، وصفحة 404 مخصصة.
- سيرة وخبرة وأعمال ومهارات وإصدارات وتعليم ودورات وتواصل.
- تنقل NDS متجاوب، فهرس أقسام، تنزيل PDF، مشاركة ونسخ رابط، وانتقال اللغة مع إبقاء القسم.
- قراءة وتنقل أساسيان بلا JavaScript؛ أصول وخطوط محلية دون CDN.
- canonical/hreflang وsitemap، وCSP مبني على بصمات المحتوى.

الهوية شخصية، وليست حكومية؛ لا ختم DGA ولا شعارات حكومية. الصورة وPDF الحاليان لم يُستبدلا في التدقيق.

## المتطلبات / Requirements

- **البناء والنشر:** Python **3.11+** فقط؛ لا npm install في Cloudflare.
- **التحقق الموسع فقط:** Node **22+**, npm، Python venv، متصفحات Playwright وأدوات `requirements-test.txt`.
- لا environment variables مطلوبة للموقع. `CHROMIUM_EXECUTABLE_PATH` و`AXE_JS_PATH` اختياريان لأدوات الاختبار فقط.

## البناء والمعاينة / Build & preview

```bash
python3 tools/build.py
python3 tools/package.py
python3 tools/serve.py --port 8000
```

افتح `http://localhost:8000/` و`http://localhost:8000/en/`.
معاينة Arena تتاح من رابط المنفذ في الواجهة، وليس localhost الخاص بجهازك.
`serve.py` يقرأ **dist/** ويطبق ترويسات الأصول و404؛ يسمح بالتضمين للمعاينة المحلية فقط. لا يحاكي كل إعادة توجيه Cloudflare، ولا يصلح خادم إنتاج. ملف `_headers` المنشور يبقى مانعًا للتضمين.

## الاختبارات / Validation

فحوص دون dependencies:

```bash
python3 tools/build.py && python3 tools/package.py
python3 tests/run_static_checks.py
python3 tests/check_docs.py
python3 tools/reproduce_nds.py  # يتطلب سجل Git كاملًا؛ بلا شبكة أو ترقية
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/check_secrets.py --history
python3 -m compileall -q tools tests
```

تهيئة أدوات التحقق الاختيارية (لا تدخل الموقع المنشور):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
npm ci --ignore-scripts
python -m playwright install --with-deps chromium firefox webkit
npm run validate
npm audit --audit-level=moderate
python tools/check_fonts.py
```

مع استمرار خادم المعاينة، شغّل من طرفية أخرى:

```bash
. .venv/bin/activate
python tests/run_checks.py http://127.0.0.1:8000
```

تشمل اختبارات المتصفح 11 عرضًا للغتين، menu/Escape وTOC واللغة وBack/Forward وshare/download و404 والطباعة وno-JS وdark و200% text وaxe-core. تُكتب النتائج الجديدة في `test-results/` المتجاهل. CI في `.github/workflows/validate.yml` يشغّل المجموعة على Chromium وFirefox وWebKit، ويتحقق من معاينة Cloudflare لنفس commit على الفروع غير الإنتاجية. لا ينشر CI ولا يغيّر إعدادات المزود؛ التكامل الموجود ينشئ المعاينة. النتائج البعيدة الفعلية في الملحق، لا تُستنتج من وجود workflow.

لإعادة الاختبار محليًا: `BROWSER=firefox TEST_RESULTS_DIR=test-results/firefox python tests/run_checks.py http://127.0.0.1:8000`، أو `BROWSER=webkit` مع مجلد أدلة منفصل.

## بنية المشروع / Structure

| المسار | الغرض |
|---|---|
| `content/content.json` | المحتوى الثنائي اللغة ومعلومات SEO والنطاق |
| `tools/build.py` | توليد HTML وsitemap وبصمات CSP |
| `index.html`, `en/index.html`, `404.html` | مخرجات مولدة ومتتبعة؛ لا تعدلها منفردة |
| `assets/css/`, `assets/js/` | NDS؛ التخصيص في `theme.css` و`site.js` فقط |
| `assets/fonts/`, `assets/img/`, `assets/docs/` | الخطوط والصورة وPDF |
| `assets/licenses/` | إشعارات الأطراف الثالثة، وليست رخصة للموقع كله |
| `tools/package.py` | إنشاء `dist/` بقائمة عامة، مع رفض symlinks وتطبيق بوابة حقوق الخطوط |
| `tools/serve.py` | معاينة الحزمة محليًا مع CSP و404 |
| `tests/` | static/unit/browser/HTML/CSS/secrets |
| `docs/` | توثيق وتقارير داخلية لا تُنشر |
| `_headers`, `robots.txt`, `sitemap.xml` | Cloudflare security وSEO |
| `vercel.json` | بديل Vercel منفصل، يُخرج `dist` أيضًا |

## تعديل المحتوى والأصول / Content & assets

عدّل JSON ثم أعد البناء والتغليف والاختبارات. عند تغيير `site.url` حدّث `robots.txt` أيضًا. يولّد البناء CSP من HTML النهائي؛ التعديل اليدوي على inline scripts/styles بعد البناء يكسر البصمات.

لا تُخترع ترجمات لحقائق السيرة أو مؤهلات جديدة. تأكيدات السيرة وحقوق الصورة في [UPDATE-CHECKLIST](docs/UPDATE-CHECKLIST.md). PDF الحالي نصي A4، وليس نسخة أصلية موقعة؛ `tools/make_cv_pdf.py --output test-results/cv-preview.pdf` يولّد **نسخة مراجعة جديدة** ولا يستبدل الملف المعتمد تلقائيًا. أداة `subset_fonts.py` القديمة أصبحت مدخلًا لفحص تغطية الخطوط للقراءة فقط؛ لا تعيد كتابة خطوط NDS.

## NDS والإتاحة / NDS & accessibility

الحزم الموروثة موسومة **`1.12.x-dev`** وليست release `v1.12.0`. لا نعرف commit upstream الدقيق لجميع تلك الحزم؛ [سجل التكامل](docs/NDS-INTEGRATION.md) يوضح المصدر المعروف والإصلاحات والبصمات وحدود conformance. لم نُجرِ ترقية تلقائية.

اختبارات Playwright وaxe الآلية، حتى مع WebKit، ليست شهادة WCAG أو اختبار Safari الحقيقي أو بديلًا عن قارئ الشاشة والأجهزة الحقيقية. لا ندعي دعم متصفحات قديمة. [مرجع الثيم](docs/DESIGN-TOKENS.md).

## النشر والترخيص / Deployment & rights

Cloudflare Pages: framework `None`، أمر البناء `python3 tools/build.py && python3 tools/package.py`، ومجلد الخرج **`dist`**. لا تنشر جذر المستودع. راجع [DEPLOY.md](DEPLOY.md).

**لا توجد رخصة عامة مختارة للمشروع**؛ يلزم قرار المالك، ولا تعني MIT الخاصة بـNDS ترخيص الصورة والسيرة أو جميع الخطوط. لذلك يستبعد `package.py` خطوط `SaudiWeb` و`Maqroo` الموروثة من الموقع المنشور ويزيل مراجعها من CSS المنسوخ؛ تبقى IBM Plex المرخصة. لم تُمنح حقوق جديدة للنسخ الموروثة المحفوظة في Git. راجع تقرير التدقيق. لا تُضف رخصة مفترضة.

## مشاكل شائعة / Troubleshooting

- `dist/` غير موجود: شغّل build ثم package.
- HTML مولد مختلف في CI: أعد build وتتبّع HTML و`_headers` و`vercel.json` مع المصدر.
- Playwright لا يجد المتصفح: نفّذ install أعلاه أو اضبط `CHROMIUM_EXECUTABLE_PATH`.
- glyph ناقص: شغّل `tools/check_fonts.py`؛ لا تضغط خطوط vendor بأداة الواجهة القديمة.
- CSP في Preview: أعد البناء وافحص الترويسات الفعلية؛ لا تُضف `unsafe-inline` أو مصادر عشوائية لإخفاء المشكلة.

المساهمة: [CONTRIBUTING.md](CONTRIBUTING.md) · الأمان: [SECURITY.md](SECURITY.md).
