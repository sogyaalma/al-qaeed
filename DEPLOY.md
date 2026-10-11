# دليل النشر وربط النطاق / Deployment & Domain Guide

## 1. المتطلبات / Requirements
- حساب GitHub أو GitLab أو Bitbucket (اختياري لكنه الأسهل للتحديث).
- حساب Vercel (مجاني للمشاريع الشخصية؛ تحقق من شروط الخطة قبل الاستخدام).
- نطاق شخصي تشتريه بنفسك (لم يُشترَ نطاق ضمن هذا المشروع).

## 2. قبل النشر / Before deploying
1. حدّث النطاق إلى نطاقك النهائي في:
   - `content/content.json` → `site.url`
   - `robots.txt` (سطر Sitemap)
2. أعد توليد الصفحات: `python3 tools/build.py`
3. تحقق من الملف `assets/docs/abdulaziz-al-qaeed-cv.pdf` وأن الصورة صحيحة الحق.
4. لا توجد متغيرات بيئة سرية مطلوبة، ولا يوجد ملف `.env`.

## 3. رفع المشروع إلى Git / Push to Git (اختياري)
```bash
cd al-qaeed-website
git init -b main
git add .
git commit -m "Initial biographical profile"
git remote add origin <YOUR_REPO_URL>
git push -u origin main
```

## 4. النشر على Vercel / Deploy on Vercel
**الطريقة أ — من لوحة Vercel:**
1. Add New → Project → استورد المستودع (أو اختر "Deploy" وارفع مجلد المشروع).
2. Framework Preset: **Other**. Build Command: **فارغ**. Output Directory: **فارغ** (الجذر).
3. اضغط Deploy.

**الطريقة ب — من سطر الأوامر:**
```bash
npm i -g vercel
cd al-qaeed-website
vercel        # أول مرة: أجب بالأسئلة، واختر Other / no build
vercel --prod
```
ملف `vercel.json` موجود ويضبط رؤوس الأمان والتخزين المؤقت وإزالة الامتداد `.html`.

## 5. ربط النطاق الشخصي / Connect a custom domain
1. في مشروع Vercel: Settings → Domains → أضف النطاق (مثل `example.com` و `www.example.com`).
2. Vercel يعرض لك سجلات DNS المطلوبة. **تحقق منها في لوحة Vercel نفسها لأنها قد تتغير.** في الغالب:

| النوع / Type | الاسم / Name | القيمة / Value |
|---|---|---|
| A | `@` (النطاق الجذري) | `76.76.21.21` |
| CNAME | `www` | `cname.vercel-dns.com` |

3. أضف هذه السجلات عند مزود النطاق (مسجّل النطاق أو DNS provider). قد يستغرق الانتشار دقائق إلى ساعات.
4. انتظر حتى يظهر النطاق بحالة **Valid Configuration** وتُصدر شهادة HTTPS تلقائيًا.
5. اختر النطاق الأساسي (apex أو www) وفعّل التحويل من الآخر إن أردت.
6. بعد ربط النطاق، غيّر `site.url` و `robots.txt` كما في القسم 2، وأعد النشر.

## 6. التحقق من نجاح النشر / Verify the deployment
- افتح الرابط الذي يعطيه Vercel، ثم النطاق الشخصي بعد انتشار DNS.
- تأكد من: الصفحة العربية تفتح على `/`، الإنجليزية على `/en/`، التنزيل يعمل على `/assets/docs/abdulaziz-al-qaeed-cv.pdf`، والقفل الأخضر لـ HTTPS.
- `https://YOUR-DOMAIN/sitemap.xml` و `https://YOUR-DOMAIN/robots.txt` يجب أن يعرضا الملفات.
- لا تعتبر الموقع منشورًا قبل أن تفتح الرابط الفعلي بنفسك.

## 7. التحديث لاحقًا / Updating later
- عدّل `content/content.json` ثم `python3 tools/build.py`، ثم ارفع التغييرات (`git push`) أو أعد `vercel --prod`.
- لإضافة مشروع أو شهادة أو خبرة: أضف عنصرًا جديدًا في المصفوفة المناسبة (`experience.items`، `training.items`، `community.groups`...) بالمفتاحين `ar` و `en`، ثم أعد التوليد.
- راجع `docs/UPDATE-CHECKLIST.md` للمعلومات التي تحتاج تأكيدًا.
