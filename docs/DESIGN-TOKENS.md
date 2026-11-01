# ثيم المشروع — مرجع التوكنات الحالي

آخر مراجعة: **2026-11-01**. الواجهة NDS Vanilla **v1.12.0**. لا `styles.css` ولا `--paper/--ink/--green`. التقارير المؤرخة في 2026-10-18 تصف الملف السابق لا هذا الملف.

التخصيص كله في `assets/css/theme.css`، في الخانة التي يحجزها `_includes/head.html` (`<link id="nds-theme-stylesheet">`). يُحمَّل بعد بوابة الـfold وقبل حقن الحزمة الحرجة، لذلك تُكتب البذور بـ`:root:root` حتى لا تخسر أمام تصحيح التباين داخل الحزمة الحرجة. هذا أسلوب الإصدار نفسه في `_sass/themes/_register.scss`.

## البذور — Custom Palette

`<html data-palette>` يشغّل محرك OKLCH. المشروع لا يعيد كتابة المنحدرات:

| البذرة | القيمة | الدور |
|---|---|---|
| `--brand-primary` | `#0e5a49` | أخضر الهوية. يشتق منه منحدر primary وألفا النص والأزرار |
| `--brand-secondary` | `#b08a4f` | الذهبي المستخدم في السيرة المطبوعة |
| `--neutral-tint` | `0.8` | حرارة الرمادي الموثقة (0 رمادي محايد، 1 افتراض الإصدار) |
| `--background-primary-strong` | `#0a3d32` | سطح عميق يوثّق `themes.md` أن البذور لا تعبّره وحدها |
| `--img-overlay-color` | `#0a3d32` | لون تغطية صورة البطل. الاسم القديم `--background-image-overlay` غير موجود في v1.12.0 |

الوضع الداكن ليس لوحة مكتوبة هنا. زر `data-theme-toggle` يضيف `dark` إلى `data-theme`، وNDS يعيد حل الدلالات من المنحدرات نفسها ويحفظ الاختيار في `nds-theme`. أول زيارة بلا اختيار محفوظ تتبع النظام عبر استثناء موثق، لا عبر لوحة ثانية. انظر [CUSTOM-EXCEPTIONS.md](CUSTOM-EXCEPTIONS.md).

المتصفح بلا `oklch(from …)` يبقى على لوحة DGA المجمدة. هذا سلوك الإصدار، وهوية خضراء متماسكة في الحالتين، لا عطل.

## مقابض المكونات

نُقلت من `style=""` لأن CSP المؤلف يمنع خصائص style. القيم هي قيم الأمثلة الكنسية:

| الصنف | المقبض | المصدر |
|---|---|---|
| `.alq-facts` | `--max-col: 2; --mid-col: 2; --min-col: 1` | `components/definition-list.md` |
| `.alq-facts-single` | الأعمدة الثلاثة = 1 | العمود الواحد في التواصل |
| `.alq-full` | `--card-width: 100%` | `components/cards.md` |
| `.alq-stack` | `--gap: var(--spacing-xl)` | `layout/flex.md` |
| `.alq-tags` | `--gap: var(--spacing-sm)` | `layout/flex.md` |
| `.alq-toc` | `--toc-skeleton-rows: 8` | `components/toc.md` |

لا مجموعة مسافات بديلة. `--spacing-xl` و`--spacing-sm` توكنات NDS.

## ما لا يفعله هذا الملف

- لا يعيد تعريف `--background-body` ولا `--text-*` ولا لوحة داكنة.
- لا يعيد تنسيق `.nds-*` خارج `@media print` (إخفاء الكروم عند الطباعة فقط).
- لا يغيّر أبعاد ملف الصورة. القص البصري القديم إلى لوحة 5:6 أُزيل؛ الصورة داخل `.nds-avatar` الكنسي.
- خطوط العرض: IBM Plex عبر حزم NDS. Cairo وReadex Pro وOpenDyslexic ملفات الإصدار لثيمات accessibility/corporate/sunset، لا تُفرض على السيرة.

[سجل التكامل](NDS-INTEGRATION.md) · [الاستثناءات](CUSTOM-EXCEPTIONS.md).
