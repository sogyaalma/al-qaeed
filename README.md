# السيرة التعريفية للشيخ عبدالعزيز القعيد / Sheikh Abdulaziz Al-Qaeed — Biographical Profile

موقع ثنائي اللغة للتعريف بالشيخ عبدالعزيز القعيد وسيرته، بالعربية (RTL) والإنجليزية (LTR). مبني بـ **HTML5 + CSS3 + Vanilla JS**، ويُنتج ملفات ثابتة للنشر؛ لا إطار واجهات ولا Backend ولا قاعدة بيانات.
A bilingual Arabic (RTL) and English (LTR) profile built with plain HTML/CSS/JavaScript. It deploys as static files—no framework runtime, backend, or database.

## المحتوى / Contents
| المسار | الوصف |
|---|---|
| `index.html` | الصفحة العربية (الافتراضية) |
| `en/index.html` | English page |
| `404.html` | صفحة الخطأ 404 |
| `assets/css/styles.css` | التصميم كله (الخطوط + الأنماط) |
| `assets/js/main.js` | تحسين تدريجي فقط: سنة الحقوق + ظهور العناصر (المحتوى مكتمل بدونه) |
| `assets/fonts/` | الخطوط مستضافة محليًا (woff2) مع ملفات الترخيص |
| `assets/img/` | الصورة الشخصية (JPG/WebP بأحجام متعددة)، وfavicon.svg |
| `assets/docs/abdulaziz-al-qaeed-cv.pdf` | ملف السيرة الذاتية للتنزيل |
| `content/content.json` | مصدر المحتوى الثنائي اللغة (ملف مصدر، لا يدخل حزمة النشر) |
| `tools/build.py` | يولّد الصفحات وملف sitemap من `content.json` |
| `tools/package.py` | ينشئ `dist/` بقائمة ملفات الموقع العامة فقط |
| `tests/run_checks.py` | اختبارات المتصفح (Playwright وaxe-core) |
| `docs/` | تقارير الاختبارات واللقطات وقائمة اعتماد المحتوى؛ لا تدخل حزمة النشر |
| `_headers` | ترويسات Cloudflare Pages الأمنية |
| `robots.txt`, `sitemap.xml` | إعدادات SEO |

> ملاحظة السيرة: ملف PDF الحالي نسخة أُنشئت من صفحتي PNG، وليس PDF أصليًا موقّعًا. راجع `docs/UPDATE-CHECKLIST.md` للتأكيدات المطلوبة قبل النشر العام. هذا الملف والوثائق الداخلية لا يُنسخان إلى `dist/`.

## البناء والمعاينة محليًا / Build and preview locally
المتطلبات: Python 3 (المكتبة القياسية فقط لبناء الموقع وتغليفه).

```bash
python3 tools/build.py
python3 tools/package.py
python3 -m http.server 8000 --bind 0.0.0.0 --directory dist
```
ثم افتح / Then open: http://localhost:8000 و http://localhost:8000/en/

## تعديل المحتوى / Editing content
1. عدّل القيم في `content/content.json` (النصوص بالعربية والإنجليزية).
2. أعد توليد الصفحات وتجهيز حزمة النشر:
   ```bash
   python3 tools/build.py && python3 tools/package.py
   ```
3. شغّل اختبارات المتصفح (تحتاج Playwright وaxe-core وChromium):
   ```bash
   pip install playwright axe-core-python
   python3 -m playwright install chromium
   python3 -m http.server 8000 --bind 0.0.0.0 --directory dist
   python3 tests/run_checks.py http://127.0.0.1:8000
   ```

**إضافة لغة ثالثة:** أضف مفتاح اللغة بجوار `ar` و`en` في `content.json`، ثم أضف اللغة إلى `LANGS` في `tools/build.py` وأنشئ المسار المقابل.

**قبل النشر:** تأكد من ضبط `site.url` في `content/content.json` ورابط sitemap في `robots.txt` على النطاق النهائي، ثم أعد التوليد والتغليف.

## الخطوط / Fonts
- IBM Plex Sans Arabic وNoto Naskh Arabic — مرخصان SIL OFL.
- Satoshi (Fontshare) — مرخص للاستخدام التجاري والويب وفق ملف الترخيص المرفق.
- الخطوط مستضافة ذاتيًا بالكامل: لا طلبات خطوط لخوادم طرف ثالث.

## النشر / Deployment
راجع `DEPLOY.md` لإعداد Cloudflare Pages ومراجعة نشر الفروع. إعداد `vercel.json` خاص بـVercel ولا يحل محل إعداد Cloudflare Pages.
