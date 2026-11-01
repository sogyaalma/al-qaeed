# NDS — التكامل الحالي / Current integration

آخر مراجعة: **2026-11-01**. هذه الوثيقة تصف التشغيل الحالي. تقرير [AUDIT-2026-10-18.md](AUDIT-2026-10-18.md) و[CONTINUATION-2026-10-18.md](CONTINUATION-2026-10-18.md) يصفان الحزم الموروثة `1.12.x-dev` قبل هذا التثبيت، ولا يصفان الأصول المنشورة الآن.

## الإصدار المثبت

| البند | القيمة المتحققة |
|---|---|
| المستودع | [mazin-musleh/NDS-vanilla](https://github.com/mazin-musleh/NDS-vanilla) |
| الوسم | `v1.12.0` (أحدث release مستقر بتاريخ 2026-11-01؛ نُشر 2026-09-05؛ ليس prerelease) |
| الالتزام | `030d1c7ff4ab5a3092c17b93429b1ac55291ea4d` |
| شريط وقت التشغيل | `1.12.0` داخل حزم JS المنسوخة |
| الرخصة | MIT — [LICENSE-NDS-vanilla.txt](LICENSE-NDS-vanilla.txt). لا ترخّص السيرة ولا الصورة ولا خطوط SaudiWeb/Maqroo |
| التعليمات | NDS IQ **3.1** في `NDS-IQ.md`. بتاريخ 2026-11-01 كان الملف على `main` مطابقًا بايتًا للملف المثبّت (blob `3dc754fcaf590f7ef84e41e0eb0f818927a1fede`). وسم `IQv3.2` موجود ولم يُستبدل الملف لأن القواعد تطلب قرار المالك قبل الاستبدال |
| الدبوس | [tools/nds-pin.json](../tools/nds-pin.json) |

لم يُستعمل فرع تطوير غير منشور. لم تُرفع الخط الأساسي إلى إصدار أحدث لأن `v1.12.0` كان أحدث release مستقر عند المراجعة.

## مصدر الأصول

`python3 tools/vendor_nds.py fetch` ينزّل tarball الوسم من `codeload.github.com` (sha256 `700bbf9a899dd57a4414cdda647a974ec14cce4be3999e0de54086e6246475c7`) إلى `.nds/` (متجاهل في Git). ملف ZIP الخاص بصفحة الـrelease (`nds-vanilla-template-v1.12.0.zip`) يحوّل إلى `objects.githubusercontent.com` وهذا المضيف غير متاح من بيئة البناء هذه، لذلك:

- JavaScript: نسخ بايتية من `assets/js/*.min.js` داخل الوسم. لا تُضاف يدويًا `nds-delegated` ولا `nds-extras`؛ `nds-main` يحمّلهما.
- CSS: يُجمَّع من SCSS الوسم بأداة Dart Sass **1.83.4** (`--style=compressed`)، مع إزالة BOM وإصلاح سطر شريط الإصدار من `_plugins/css_banner_format.rb`.
- بوابة الرسم الأول: `_sass/_fold.scss` مع `$inline:true`، كما يفعل `_includes/critical-inline.html`.
- `built_site_twin`: **غائب**. لا مقارنة بصرية بقالب `_site` المبني من ZIP الـrelease، لأن ذلك الأرشيف غير قابل للتنزيل هنا. لا تُدّعى مطابقة بصرية كاملة.

`sync` يكتب الأصول و`docs/nds-assets.json` (38 بصمة vendor). `verify` يرفض أي اختلاف. `assets/css/theme.css` و`assets/js/site.js` مملوكان للمشروع وليسا في بصمات الـvendor.

أُزيلت أدوات الإصلاح الموروثة (`tools/repair_nds_css.py` و`tools/build_hgi.py` و`tools/reproduce_nds.py` و`tools/vendor/`). إصدار v1.12.0 لا يحتوي `data:` في خطوط CSS، ويشحن ورقة HGI الرسمية كاملة، فلا حاجة لإصلاح BOM ولا لاقتطاع 22 قاعدة.

## ماذا يُحمَّل في كل نوع صفحة

ترتيب الرأس يتبع `_includes/head.html`: charset، viewport، title، description، preload للصورة (صفحات السيرة فقط)، بوابة الـfold مضمّنة، preload للحزمة الحرجة، ثم `<link id="nds-theme-stylesheet">`، ثم preload لـ`nds-main.min.css` و`nds-accessibility.min.css`، ثم الأيقونة والـcanonical. سكربت الرأس الكنسي يحوّل الـpreload إلى stylesheet، وتحته عنصر التفضيل النظامي (الاستثناء 2).

| الصفحة | CSS في الرأس | JS في نهاية الجسم | ما يحمّله وقت التشغيل عند الحاجة |
|---|---|---|---|
| `/` و`/en/` و`404.html` | fold + critical + theme.css + main + accessibility | `nds-main.min.js` و`nds-accessibility.min.js` و`site.js` (نوع module) | `nds-delegated.min.js` و`nds-extras.min.js` و`nds-audit.min.js` و`nds-icons.min.css` و`hgi-rounded-stroke-min.css` |
| `/nds-showcase/` | نفسه، بلا preload للصورة، ومع `noindex,nofollow` | `nds-main.min.js` و`nds-accessibility.min.js`. لوحة الإتاحة تُضمَّن في الفهرس وصفحة accessibility فقط. `site.js` لا يُحمَّل | الحزم نفسها. لا يُشحن `nds-showcase.min.js` (سكربت موقع التوثيق فقط) |

`site.js` لا يعيد بناء القائمة ولا scrollspy ولا المشاركة ولا الثيم. يحدّث رابط تبديل اللغة ليبقي شظية القسم بين الصفحتين الثابتتين.

لا تُحمَّل حزم chart/code/cookie-consent/editor المنفصلة: وسم v1.12.0 لا يشحنها كملفات. الإشارة الداخلية إلى chart/editor داخل `nds-main` ليست ملفات ناقصة.

## الثيم

العلامة عبر الآلية الموثقة لا عبر محرك خاص:

1. `<html data-palette>` يشغّل منحدر OKLCH في `_sass/themes/_register.scss`.
2. `theme.css` يبذر `--brand-primary: #0e5a49` و`--brand-secondary: #b08a4f` و`--neutral-tint: 0.8`، ويضبط `--background-primary-strong` و`--img-overlay-color`.
3. الوضع الداكن رمز `dark` في `data-theme`، يكتبه زر `data-theme-toggle` ويحفظه NDS في `localStorage` بالمفتاح `nds-theme`. أول زيارة بلا قيمة محفوظة تتبع `prefers-color-scheme` بالعنصر المنفصل (الاستثناء 2).
4. لا لوحة داكنة مكتوبة يدويًا. المتصفحات بلا CSS relative colour تبقى على لوحة DGA المجمدة، وهذا سلوك الإصدار الموثق.

التفاصيل والاستثناءات: [CUSTOM-EXCEPTIONS.md](CUSTOM-EXCEPTIONS.md) و[DESIGN-TOKENS.md](DESIGN-TOKENS.md).

## المكونات في السيرة

الـmarkup يُولَّد من `tools/nds_shell.py` و`tools/build.py` وفق أمثلة الوسم، لا من ذاكرة أسماء الأصناف. الشكل المطابق: `examples/faculty-cv.md` مع `layout/page-shell.md` و`ui-shell/{mainnav,hero,footer}.md` و`components/{toc,stepper,cards,definition-list,tags,alert}.md`.

لا قائمة تنقل عامة إلى المعرض. المعرض مسار مراجعة منفصل: `/nds-showcase/`، و`noindex`، وخارج `sitemap.xml`. تغطيته في [NDS-SHOWCASE.md](NDS-SHOWCASE.md).

أقسام السيرة تُبنى من `PROFILE_SECTIONS` في `tools/build.py`. قسم لاحق = كائن في `content/content.json` + مدخل `nav` بمعرّف الغلاف + دالة عرض. لا تُخترع أقسام فارغة.

## التهيئة ودورة الحياة

1. سكربت الرأس يختم `data-theme` قبل الرسم الأول ثم يحوّل روابط preload.
2. `nds-main.min.js` (defer) يهيئ المكونات الحاضرة في الصفحة ويحمّل الحزم الكسولة.
3. `nds-accessibility.min.js` يهيئ زر اللوحة ويحمّل `assets/i18n/accessibility/{lang}.json`.
4. لا إطار عمل ولا mount/unmount لتطبيق. الصفحات ثابتة، لذلك لا مستمعات مكررة من إعادة تركيب.
5. CSP: `build.py` يحسب بصمات عناصر `<script>` و`<style>` النهائية ويكتبها في `_headers` و`vercel.json`. لا `unsafe-inline` للسكربتات ولا `unsafe-eval`. `style-src-attr 'unsafe-inline'` لأن مكونات NDS تكتب خصائص style في وقت التشغيل؛ HTML المؤلف بلا خصائص style.

## ما لا يُدّعى

- ليست مطابقة WCAG كاملة لأن NDS مستخدم. فحص html-validate الصارم على صفحات السيرة نجح محليًا؛ فحوص المتصفح وaxe وقارئ الشاشة لم تُعد تشغيلها في بيئة هذا التغيير (لا متصفح مثبّت). CI يشغّلها على Chromium وFirefox وWebKit.
- ليست مطابقة بصرية لقالب `_site`، لأن أرشيف الـrelease غير متاح هنا.
- نماذج المعرض واجهة فقط. لا إرسال ناجح إلى خادم.

إجراء التحديث: [UPDATE-CHECKLIST.md](UPDATE-CHECKLIST.md).
