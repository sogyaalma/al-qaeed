# السيرة التعريفية للشيخ عبدالعزيز القعيد / Sheikh Abdulaziz Al-Qaeed — Biographical Profile

موقع ثنائي اللغة للتعريف بالشيخ عبدالعزيز القعيد وسيرته، بالعربية (RTL) والإنجليزية (LTR).
A bilingual Arabic (RTL) and English (LTR) profile.

الواجهة مبنية على **[NDS-vanilla](https://github.com/mazin-musleh/NDS-vanilla)** (نظام التصميم الوطني، تنفيذ HTML/CSS/JS خالص). المحتوى يُولَّد من JSON إلى صفحات ثابتة؛ لا إطار تشغيل ولا Backend ولا قاعدة بيانات.
The UI uses **NDS-vanilla** (Saudi National Design System, plain HTML/CSS/JS). Pages are generated as static files—no framework runtime, backend, or database.

> الهوية البصرية هنا شخصية (أخضر ورقي). شعار الهيئة والختم الرقمي ورؤية 2030 غير مستخدمة، وفق إخلاء مسؤولية NDS للمشاريع غير الحكومية.
> Visual identity is personal. DGA stamp, government logos, and Vision 2030 artwork are not used, per the NDS disclaimer for non-government projects.

## المحتوى / Contents
| المسار | الوصف |
|---|---|
| `index.html` | الصفحة العربية (الافتراضية) |
| `en/index.html` | English page |
| `404.html` | صفحة الخطأ 404 |
| `assets/css/` | NDS critical/main/icons + `theme.css` (توكنات الهوية) |
| `assets/js/` | مكتبة NDS (`nds-main.min.js` والملفات التابعة) |
| `assets/fonts/` | خطوط NDS المستضافة محليًا (IBM Plex Sans Arabic + أيقونات HGI) |
| `assets/img/` | الصورة الشخصية، favicon، رسم 404 |
| `assets/docs/abdulaziz-al-qaeed-cv.pdf` | ملف السيرة الذاتية للتنزيل |
| `assets/i18n/` | حزم ترجمة مكوّنات NDS |
| `content/content.json` | مصدر المحتوى الثنائي اللغة |
| `tools/build.py` | يولّد الصفحات وملف sitemap من `content.json` بترميز NDS |
| `tools/package.py` | ينشئ `dist/` بقائمة ملفات الموقع العامة فقط |
| `NDS-IQ.md` | قواعد بناء الواجهة مع NDS (لا تُعدَّل) |
| `tests/run_static_checks.py` | فحوص build/package والروابط والأصول (Python قياسي) |
| `tests/run_checks.py` | اختبارات المتصفح (Playwright وaxe-core وChromium) |
| `docs/` | تقارير داخلية؛ لا تدخل حزمة النشر |
| `_headers` | ترويسات Cloudflare Pages الأمنية |
| `robots.txt`, `sitemap.xml` | إعدادات SEO |

> ملاحظة السيرة: ملف PDF الحالي نسخة أُنشئت من صفحتي PNG، وليس PDF أصليًا موقّعًا. راجع `docs/UPDATE-CHECKLIST.md` للتأكيدات المطلوبة قبل النشر العام. هذا الملف والوثائق الداخلية لا يُنسخان إلى `dist/`.

## البناء والمعاينة محليًا / Build and preview locally

```bash
python3 tools/build.py
python3 tools/package.py
python3 -m http.server 8000 --bind 0.0.0.0 --directory dist
```

ثم افتح / Then open: http://localhost:8000 و http://localhost:8000/en/

## تعديل المحتوى / Editing content
1. عدّل القيم في `content/content.json`.
2. أعد التوليد والتغليف:
   ```bash
   python3 tools/build.py && python3 tools/package.py
   python3 tests/run_static_checks.py
   ```

**قبل النشر:** تأكد من ضبط `site.url` في `content/content.json` ورابط sitemap في `robots.txt`.

## نظام التصميم / Design system
- NDS Vanilla **1.12.x-dev** — أصول التشغيل في `assets/` (لا تُحرَّر يدويًا).
- تخصيص الهوية فقط عبر `assets/css/theme.css` (إعادة ربط التوكنات الدلالية).
- تعليمات الوكلاء: `NDS-IQ.md` + `AGENTS.md`.

## النشر / Deployment
راجع `DEPLOY.md` لإعداد Cloudflare Pages. أمر البناء: `python3 tools/build.py && python3 tools/package.py` ومجلد الإخراج `dist`.
