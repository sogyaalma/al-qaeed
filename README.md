# موقع عبدالعزيز القعيد الشخصي / Abdulaziz Al-Qaeed — Personal Site

موقع ثنائي اللغة (عربي RTL افتراضيًا، English LTR) مبني بـ **HTML5 + CSS3 + Vanilla JS** بدون framework وبدون خطوة بناء للنشر.
A bilingual static site (Arabic RTL by default, English LTR). Plain HTML/CSS/JS — no framework, no build step to deploy.

## المحتوى / Contents
| المسار | الوصف |
|---|---|
| `index.html` | الصفحة العربية (الافتراضية) |
| `en/index.html` | English page |
| `404.html` | صفحة الخطأ 404 |
| `assets/css/styles.css` | التصميم كله (الخطوط + الأنماط) |
| `assets/js/main.js` | تحسين تدريجي فقط: سنة الحقوق + ظهور العناصر (الصفحة مكتملة بدونه) |
| `assets/fonts/` | الخطوط مستضافة محليًا (woff2) مع ملفات الترخيص |
| `assets/img/` | الصورة الشخصية (JPG/WebP بأحجام متعددة)، وfavicon.svg |
| `assets/docs/abdulaziz-al-qaeed-cv.pdf` | ملف السيرة الذاتية للتنزيل (انظر ملاحظة أدناه) |
| `content/content.json` | **مصدر المحتوى الوحيد** (عربي وإنجليزي) |
| `tools/build.py` | يولّد الصفحات من `content.json` |
| `tests/run_checks.py` | اختبارات المتصفح (Playwright) |
| `docs/` | تقرير الاختبارات، Lighthouse، قائمة التحديث، لقطات الشاشة |
| `robots.txt`, `sitemap.xml`, `vercel.json` | SEO والإعدادات الأمنية عند النشر على Vercel |

> ملاحظة السيرة: الملف المرفق كان صفحتين PNG وليس PDF أصلي، لذلك أُنشئ منه PDF بعنوان "abdulaziz-al-qaeed-cv.pdf". إن توفر PDF أصلي، استبدل الملف بالنسخة الأصلية بنفس الاسم.

## التشغيل محليًا / Run locally
المتطلبات: Python 3 (أي إصدار حديث). لا حاجة لتثبيت أي حزم للتشغيل.

```bash
cd al-qaeed-website
python3 -m http.server 8000
```
ثم افتح / Then open: http://localhost:8000 و http://localhost:8000/en/

## تعديل المحتوى / Editing content
1. عدّل القيم في `content/content.json` (كل نص له مفتاحان `ar` و `en`).
2. أعد توليد الصفحات:
   ```bash
   python3 tools/build.py
   ```
3. شغّل الاختبارات (اختياري لكن موصى به، تحتاج Playwright):
   ```bash
   pip install playwright axe-core-python && python3 -m playwright install chromium
   python3 tests/run_checks.py http://127.0.0.1:8000
   ```

**إضافة لغة ثالثة:** أضف مفتاح اللغة (مثل `fr`) بجوار كل `ar`/`en` في `content.json`، ثم أضف اللغة إلى `LANGS` في `tools/build.py` (الاتجاه، المسار) وأنشئ المسار المقابل.

**قبل النشر:** غيّر `https://www.example.com` في `content/content.json` (حقل `site.url`) وفي `robots.txt` إلى النطاق الفعلي، ثم أعد توليد الصفحات.

## الخطوط / Fonts
- IBM Plex Sans Arabic (عربي + لاتيني) و Noto Naskh Arabic — مرخصان SIL OFL.
- Satoshi (Fontshare) — مجاني للاستخدام التجاري والويب.
- الخطوط مستضافة ذاتيًا بالكامل: لا طلبات لخوادم طرف ثالث.

## النشر / Deployment
راجع `DEPLOY.md` لخطوات النشر على Vercel وربط النطاق.
See `DEPLOY.md` for Vercel deployment and custom-domain steps.
