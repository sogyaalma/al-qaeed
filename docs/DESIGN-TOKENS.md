# ثيم المشروع — مرجع التوكنات الحالي

آخر مراجعة: 2026-10-18. الواجهة NDS فعلية؛ لم يعد `styles.css` أو `--paper/--ink/--green` جزءًا من التنفيذ. التقارير القديمة تاريخية.

التخصيص في `assets/css/theme.css` بعد NDS critical/main، دون إعادة تعريف reset أو framework آخر.

| المجال | التوكنات الفعلية |
|---|---|
| الأسطح | `--background-body`, `--background-stripe`, `--background-card`, `--background-nav`, `--background-sub-hero` |
| العلامة | `--background-primary`, `--background-primary-strong`, `--background-primary-light`, `--background-hero`, `--background-footer`, `--background-image-overlay` |
| النص | `--text-display`, `--text-default`, `--text-primary-paragraph`, `--text-secondary-paragraph`, `--text-primary-strong` |
| ضبط layout موثق | `.alq-facts`: max/mid/min-col؛ `.alq-full`: card-width؛ `.alq-stack/.alq-tags`: gap؛ `.alq-toc`: toc-skeleton-rows |

القيم الفاتحة ورقية/خضراء، ولكل تخصيص مقابل تحت `:root[data-theme~="dark"]`.
لا توجد مجموعة بديلة من توكنات المسافات؛ تُستهلك `--spacing-xl` و`--spacing-sm` الخاصة بـNDS.
التوكنات الدلالية لا تعيد تلوين كل زر NDS تلقائيًا؛ حالات المكونات تأتي من component tokens الخاصة بالمكتبة. لا ندعي أن جميع درجات أخضر NDS أعيد تعريفها.

قواعد الصيانة:
1. استخدم knobs ثم semantic tokens قبل overrides، واقرأ مصدر المكون قبل تغييره.
2. لا تكتب فوق vendor يدويًا. استثناء encoding/asset URL محدود وموثق وقابل لإعادة التنفيذ في `repair_nds_css.py`.
3. مرر RTL/LTR وdark وfocus وreduced motion وno-JS بعد أي تعديل.
4. خواص CSS الخاصة بالصورة تقصها بصريًا فقط إلى avatar 120px؛ ملف الصورة لم يتغير وأبعاد HTML الأصلية 480×432.
5. قواعد الطباعة محصورة في `.alq-site` و`@page A4`، وتحذف chrome والأفعال من نسخة القراءة دون حذف محتوى السيرة.

[سجل التكامل](NDS-INTEGRATION.md) · [التدقيق الحالي](AUDIT-2026-10-18.md).
