# النشر على Cloudflare Pages / Cloudflare Pages Deployment

الموقع static بالكامل. لا يحتاج إلى Backend أو قاعدة بيانات أو Pages Functions أو Workers.

## 1. إعداد مشروع Cloudflare Pages

في مشروع Pages المرتبط بالمستودع، استخدم الإعدادات التالية لتوليد حزمة عامة منفصلة عن ملفات المصدر والتوثيق:

| الإعداد | القيمة |
|---|---|
| Framework preset | `None` |
| Root directory | جذر المستودع (الافتراضي) |
| Build command | `python3 tools/build.py && python3 tools/package.py` |
| Build output directory | `dist` |
| متغيرات البيئة | لا توجد متغيرات مطلوبة لهذا الموقع |

يتضمن `tools/package.py` فقط الصفحات والأصول المطلوبة و`robots.txt` و`sitemap.xml` و`_headers` في `dist/`. لا ينشر `docs/` أو `tests/` أو `tools/` أو `content/` أو ملفات README/DEPLOY.

> إذا كان إعداد المشروع الحالي ينشر جذر المستودع مباشرةً، غيّر مجلد الإخراج إلى `dist` قبل اعتماد النشر. لا يكفي وجود `dist/` في المستودع ما لم يوجّه إعداد Pages إليه.

## 2. المعاينة ومراجعة الفروع

- اجعل فرع الإنتاج هو الفرع المعتمد لديك (غالبًا `main`).
- فعّل معاينات الفروع من إعدادات Git integration في Pages، ثم راجع عنوان المعاينة الذي ينشأ للفرع قبل دمجه.
- لا أستطيع تغيير إعدادات لوحة Cloudflare من ملفات المستودع؛ إعدادات الفرع الإنتاجي والمعاينة يجب تأكيدها في لوحة Pages.

## 3. النطاق وSEO

عند تغيير النطاق عن `https://al-qaeed.pages.dev`:
1. حدّث `site.url` في `content/content.json`.
2. حدّث رابط sitemap في `robots.txt`.
3. شغّل `python3 tools/build.py && python3 tools/package.py`.
4. تحقّق من canonical وOpen Graph و`hreflang` في الصفحتين، ومن روابط `robots.txt` و`sitemap.xml` بعد النشر.

تُدار إضافة النطاق وDNS وHTTPS من لوحة Cloudflare وفق القيم التي تعرضها المنصة؛ لا تُنسخ سجلات DNS من مزود آخر دون تحقق.

## 4. المسارات والترويسات

- العربية: `/` من `index.html`.
- الإنجليزية: `/en/` من `en/index.html`.
- الخطأ: `404.html` في جذر حزمة النشر.
- لا توجد قواعد إعادة كتابة لازمة للمسارات الحالية، ولا يوجد ملف `_redirects`.
- ملف `_headers` يضع ترويسات الأمان على Cloudflare Pages. بعد نشر Preview، تحقّق من الترويسات الفعلية ومن تحميل CSS وJavaScript والصور والخطوط.
- أسماء الأصول الحالية غير مبصّمة؛ لا تستخدم immutable طويلًا عليها. إعداد Vercel البديل يستخدم إعادة التحقق بدل سنة immutable. لا يُطبق هذا الملف على Cloudflare.
- يولّد `build.py` بصمات CSP إلى `_headers` و`vercel.json` مع HTML. يُمنع تعديل inline script/style في المخرجات منفردة.
- `font-src` محصور في self؛ خط fallback مستضاف محليًا. استثناء خصائص style لمكونات NDS لا يسمح بتنفيذ inline JavaScript.

## 5. التحقق من Preview

افتح رابط Preview واختبر:
- `/` و`/en/`، ومبدّل اللغة وروابط الأقسام.
- تنزيل `/assets/docs/abdulaziz-al-qaeed-cv.pdf`.
- صفحة 404 مع حالة HTTP المناسبة.
- `/robots.txt` و`/sitemap.xml`.
- صور WebP والخطوط وترويسات الأمان في أدوات المطور.
- أحجام العرض العربية والإنجليزية الواردة في `tests/run_checks.py`.

## 6. تحديث المحتوى محليًا

```bash
python3 tools/build.py
python3 tools/package.py
python3 tests/run_static_checks.py
```

اختبر الحزمة في متصفح محليًا (يتطلب تهيئة أدوات الاختبار كما في README، ومنها Playwright وaxe-core وChromium):

```bash
python3 tools/serve.py --port 8000
python3 tests/run_checks.py http://127.0.0.1:8000
```

## 7. Vercel كخيار منفصل

يوجد `vercel.json` لإعداد Vercel بديلًا، لكنه **ليس إعداد Cloudflare Pages**. إذا استُخدم Vercel لاحقًا، اختبر توافق `cleanUrls` و`trailingSlash` مع الروابط canonical، والإعداد الحالي يبني `dist/` فقط، يوحد trailing slash للمسارات ويعيد التحقق من الأصول غير المبصّمة بدل immutable. لم يُختبر نشر Vercel بعيدًا.

## 8. بوابة الاعتماد

قبل الإنتاج: راجع [تقرير التدقيق](docs/AUDIT-2026-10-18.md) و[تأكيدات المحتوى](docs/UPDATE-CHECKLIST.md)، واعتمد حقوق المحتوى والصورة وPDF ورخصة ملفات المشروع. خطوط SaudiWeb/Maqroo غير مثبتة الحقوق مستبعدة الآن من `dist/` مع مراجع URL الخاصة بها؛ لا تنشر نسخها المرجعية الموجودة في المستودع. لا تعني صلاحية الحزمة التقنية اكتمال حقوق النشر.

خادم `tools/serve.py` للمعاينة المحلية فقط: يخفف **framing فقط محليًا** لإتاحة Arena، ولا يغيّر `_headers` المنشور. لا يحاكي URL normalization الخاصة بـPages؛ فحص `/index.html` و`/en` و`/en/index.html` إلى canonical الصحيح مع HTTPS والترويسات و404 مطلوب على Preview فعلي. نجح إنشاء Preview للفرع عبر التكامل الموجود؛ لا نشر إنتاج أو تعديل DNS. التحقق الفعلي ونتائجه في [ملحق الاستكمال](docs/CONTINUATION-2026-10-18.md).
