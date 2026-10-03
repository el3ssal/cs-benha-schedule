# تصميم موقع جدول محاضرات حاسبات بنها (cs-benha-schedule)

- **التاريخ:** 2026-10-03
- **الحالة:** معتمد (approved) بعد مراجعة الأقسام 1–4 وإضافة 5–7
- **المصدر:** `C:\Users\ahmed\Desktop\coll\جدول العام (1)-1.pdf` (33 صفحة)

---

## 0. المشكلة الحالية

- `https://cs-benha-schedule.floot.app/` هو غلاف Floot يلفّ iframe على `https://ahmedawadfathy.github.io/scheadel/`.
- الموقع الملفوف = ملف HTML واحد فيه `const DATA` متجمّد: 1561 محاضرة، 137 (مستوى/مجموعة أو تخصص/سكشن)، 4 مستويات، 6 أيام، 33 صفحة مفهرسة. لا يوجد fetch، لا localStorage، لا رفع ملفات (رغم نص الفوتر "ارفعها لتحديث الموقع").
- أي تغيير في جدول الكلية = إعادة بناء يدوية. هذا التصميم يحلّ ذلك.

**الهدف:** موقع ثابت مستقل، مينيمال مودرن بـ palette فاتح، يُحدَّث من مصدر واحد (PDF) مع 3 مداخل للتحديث، ويعيش طول السنة الدراسية.

**قرارات معتمدة من Ahmed:** Vanilla HTML/CSS/JS · GitHub Pages · PDF كمصدر حقيقة + Google Sheets كلوحة تعديل فوقه · إسقاط أرقام الجلوس (غير موجودة في الـ PDF) · كل المميزات التانية (حفظ الاختيارات، تصدير/طباعة، PWA، مقارنة النسخ).

---

## 1. بنية المشروع

```
cs-benha-schedule/
├─ index.html                     # الواجهة (RTL، lang=ar)
├─ css/
│  ├─ style.css                   # الأنماط الأساسية (design tokens)
│  └─ print.css                   # @media print — أزرار الطباعة/التصدير
├─ js/
│  ├─ app.js                      # التحكم: الاختيارات + الرندر
│  └─ data.js                     # تحميل/Validation لـ schedule.json
├─ data/
│  ├─ schedule.json               # [يُولَّد] الأحداث — المصدر للواجهة
│  ├─ overrides.json              # نسخة محلية من تبويب overrides في الشيت (cache يقرأه الـ Action)
│  └─ meta.json                   # timestamp + git sha + عدد الأحداث + hash الـ PDF
├─ pdf/
│  └─ جدول-العام.pdf              # المصدر (يُبدَّل ويُدفَع)
├─ tools/
│  ├─ extract_schedule.py         # PDF → schedule.json
│  ├─ diff_schedule.py            # مقارنة نسختين → report.md
│  ├─ sheet_sync.py               # كتابة المرايا + قراءة overrides من Sheets
│  └─ requirements.txt            # pdfplumber, pypdf, gspread, oauth2client
├─ fonts/                         # Cairo/IBM Plex Sans Arabic — subset woff2
├─ icons/                         # PWA icons (192/512) + favicon
├─ assets/                        # manifest icons, OG image
├─ tests/
│  ├─ fixtures/                   # صفحات PDF مرجعية + DATA المرجعي (scheadel)
│  ├─ test_extract.py             # اختبارات وحدة للاستخراج
│  └─ test_diff.py                # اختبارات الديف
├─ .github/workflows/
│  ├─ update.yml                  # PDF/شيت اتغيّر → استخراج → نشر
│  └─ ci.yml                      # تشغيل الاختبارات على كل push
├─ manifest.json                  # PWA manifest
├─ sw.js                          # Service Worker — لازم في الجذر (scope) 
├─ .nojekyll                      # منع معالجة Jekyll
├─ .gitignore                     # .env, service-account.json, __pycache__
├─ requirements-dev.txt
└─ README.md
```

**قواعد:**
- 🔴 `tools/requirements.txt` إلزامي — بدونه الـ Action يفشل على runner نضيف.
- 🔴 `.nojekyll` فارغ في الجذر — يمنع أخطاء "Page build failed" المتقطعة.
- 🔴 `fonts/` subset مضمّن (لا Google Fonts CDN): كل وزن عربي ≥150KB، الـ subset ينزله لـ ~30–40KB. الأرقام لاتينية + عربية فقط.
- 🔴 `.gitignore` يمنع commit أي سر (`*.json` لحساب الخدمة، `.env`).

---

## 2. خط التحديث (3 مداخل → نفس الـ Action)

### 2.1 المدخل 1 — الترمنال (الأساسي)
```
استبدل pdf/جدول-العام.pdf
git add pdf/ && git commit -m "update: schedule YYYY-MM" && git push
```
→ `update.yml` يلتقط التغيير على `pdf/**` ويشغّل الاستخراج.

### 2.2 المدخل 2 — فورم الرفع على الموقع
- `<form>` في `index.html` (مخفي خلف زر "تحديث الجدول") → يبعت الـ PDF إلى **Google Apps Script web app**.
- 🔴 **الأمن:**
  - `passcode` يتحوَّل client-side SHA-256 ويتطابق مع `PASSCODE_HASH` في Script Properties — بدونه الطلب يترفض.
  - التحقق server-side: الـ Content-Type = `application/pdf`، الاسم ينتهي بـ `.pdf`، الحجم ≤ 5MB.
  - GAS بيعمل rate-limit بسيط (مثلاً 5/دقيقة/IP) عبر Properties.
- 🔴 **رفع الملف على GitHub:** الـ Contents API عمليًا محدود (~1MB بعد base64) → استخدم **Git Data API** (`POST /git/blobs` → tree → commit) أو تحقق من الحجم وارفض الأكبر.
- الـ PAT مخفي في **Script Properties** (server-side) — لا يظهر في مصدر الصفحات أبدًا.
- الـ commit بـ PAT (مش `GITHUB_TOKEN`) → **بيشغّل الـ Action تلقائيًا** (مخالفة لقاعدة GITHUB_TOKEN التي لا تعيد تشغيل الـ workflow).

### 2.3 المدخل 3 — Google Sheets (تعديلات من الموبايل)
- الشيت فيه تبويبين:
  - `mirror` (للعرض فقط — يكتبه `sheet_sync.py` بعد كل استخراج).
  - `overrides` (المصدر للتعديلات) بـ schema صريح:
    ```json
    {
      "op": "update" | "delete" | "add",
      "key": {"day":"السبت","level":"1","group":"1","section":"1","start":"9:00"},
      "set": {"text":"...", "end":"10:30", "start":"9:00"},
      "note": "سبب التعديل",
      "author": "Ahmed",
      "date": "2026-10-03"
    }
    ```
- الـ Action: استخراج من PDF → تطبيق `overrides` → نشر. الـ key غير موجود في `op:add` = إضافة صريحة.
- 🔴 **لا يوجد way-back بدون `note` و`date`** — كل override يتسجل ويُطبَّق على ناتج جديد (مش على نسخة قديمة)، فالتعديل يعبر عن التحديثات اليدوية الدائمة.

### 2.4 `update.yml` (خطوات)
1. checkout + تثبيت `tools/requirements.txt`
2. `extract_schedule.py pdf/*.pdf --out data/schedule.json --report extract-report.md`
3. جلب `overrides` من الشيت عبر **service account** (`gspread`) وتطبيقها — مسار واحد فقط (نفس الـ Secret المستخدم في `sheet_sync.py`)
4. `diff_schedule.py` بالنسخة السابقة → `diff-report.md` (artifact + تعليق على commit)
5. اختبارات الوحدة (`tests/`) — تفشل؟ يتوقف النشر
6. كتابة `meta.json` + commit + deploy Pages

### 2.5 الأسرار (GitHub Secrets)
| الاسم | الاستخدام |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | قراءة/كتابة الشيت من الـ Action |
| `SHEET_ID` | معرف الشيت |
| `PAGES_DEPLOY_TOKEN` | (اختياري) لو استخدمنا الـ deploy API بدل `actions/deploy-pages`) |

`GAS_WEBAPP_URL` و`PASSCODE_HASH` يعيشان في **Apps Script Properties** (server-side).

---

## 3. الواجهة والتصميم (مينيمال مودرن · فاتح)

### 3.1 Design tokens
```css
--bg:        #FAFAF8;   /* خلفية دافئة */
--surface:   #FFFFFF;   /* الكروت */
--ink:       #1A1A1A;   /* النص الأساسي */
--muted:     #6B7280;   /* نص ثانوي */
--line:      #E5E7EB;   /* حدود */
--primary:   #2563EB;   /* أساسي */
--primary-soft: #EFF6FF;/* لمسة */
--ring:      rgba(37,99,235,.35); /* focus */
--radius-card: 18px; --radius-control: 12px;
--shadow-card: 0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06);
```
- متباينات (contrast) ≥4.5:1 للنص الأساسي و≥3:1 للعناصر الكبيرة — متحقق منها في `tests/` (lighthouse/manual).

### 3.2 Typography
- **Cairo** أو **IBM Plex Sans Arabic** — subset مضمّن في `fonts/` (عربي + أرقام لاتينية + علامات ترقيم).
- مقياس: `--fs-hero: clamp(26px,4vw,38px)` · body 16px/1.7 · caption 13px.
- الأوقات `direction: ltr` داخل عناصر `.time` عشان `09:00 - 10:30` ما يتقفلش.

### 3.3 Layout (RTL)
```html
<html lang="ar" dir="rtl">
<meta name="theme-color" content="#FAFAF8">
```
1. **Header خفيف**: brand mark + kicker «جامعة بنها · كلية الحاسبات والذكاء الاصطناعي» + `<h1>` + سطر تعريفي.
2. **شريط الاختيار**: 3 حقول (المستوى / المجموعة أو التخصص / السكشن) — pills على الديسكتوب، selects على الموبايل، مع ملخّص (pills) للاختيار الحالي.
3. **مواعيد النهارده**: كارت بارز (`--primary-soft` خفيف) — لو مفيش محاضرات: حالة فاضية مكتوبة.
4. **باقي الأسبوع**: شبكة `repeat(auto-fit,minmax(280px,1fr))`، كل يوم كارت، مرتّبة حسب وقت البداية.
5. **Toggle**: «عرض الأسبوع كاملًا».
6. **Futer**: مصدر البيانات + تاريخ آخر تحديث (من `meta.json`) + زر «تحديث الجدول» (الرفع).
7. **أزرار**: طباعة/PDF (`window.print`) + مشاركة رابط الاختيار (`?level=..&group=..&section=..`).

### 3.4 المكونات والحالات
- `.event`: grid `140px 1fr` — الوقت (شارة) + اسم المادة + التفاصيل (المدرّب/القاعة/«أونلاين»).
- حالات: loading (skeleton) · error (فشل تحميل `schedule.json`) · empty (يوم بلا محاضرات) · offline (بيانات الـ SW cache).
- Micro-interactions: fade/slide 150–220ms، **محترمة لـ `prefers-reduced-motion`**، focus rings بـ `--ring`.
- `aria-live="polite"` على منطقة النتائج حتى يسمعها قارئ الشاشة عند تغيير الاختيارات.

### 3.5 الطباعة (`css/print.css`)
- إخفاء Header/الفوتر/الأزرار، إظهار جدول الأسبوع كاملًا في صفحة واحدة، ألوان محايدة (`print-color-adjust: exact` للعناصر الملوّنة)، ترقيم الصفحات، ورأس باسم الطالب/المستوى/السكشن.
- منفصل عن `style.css` حتى لا يثقل التحميل العادي.

---

## 4. خط الاستخراج من الـ PDF

### 4.1 بنية الـ PDF (مُتحقَّق منها)
- 33 صفحة، `841×595` (A4 أفقي)، صفحة واحدة لكل (يوم × شريحة مستويات).
- شبكة `find_tables()`: **12 عمود فترات 45 دقيقة** (العمود الأقصى يمينًا = الفترة 1 @09:00، الأقصى يسارًا = الفترة 12 @17:15) + عمود «رقم الصف» (الأقسام) + عمود تسميات (المستوى / المجموعة أو التخصص).
- **اليوم مكتوب في هيدر الصفحة** (`السبت`…) — مصدر ربط الصفحة بيومها.
- النص عربي بـ presentation forms + اتجاه بصري معكوس.

### 4.2 خوارزمية الاستخراج (`tools/extract_schedule.py`)
1. `pdfplumber.open()` → لكل صفحة `page.find_tables()` (strategy=`lines`) + `page.extract_words()`.
2. استنتاج الـ grid من هيدر الأوقات (معاملات `09:00 … 17:15`) — يتحقق أن الصفحات كلها بنفس التخطيط؛ لو اختلف → يوقف بخطأ واضح بدل ما يطلّع بيانات غلط.
3. لكل خلية مشغولة: تحديد **span** الخلايا عن طريق `table.rows`/الحواف (`edges`) — محاضرة 90 دقيقة = خليّتان مدمجتان، فالـ span يعطي `start` (آخر فترة في النطاق بصريًا) و`end` (نهاية الفترة الأولى في النطاق).
4. قراءة تسميات الصف (المستوى/المجموعة/التخصص/رقم القسم) من عمود التسميات على يمين/يسار كل صف.
5. **معالجة النص:**
   - `unicodedata.normalize('NFKC')` (تحويل الحروف المتشكلة `ﻟ`→`ل`).
   - قلب النص (`[::-1]`) ثم **إصلاح الأرقام**: قلب كل `run` من `[0-9:.]` مرة تانية (مهم: من غير كده `14` تبقى `41`).
   - تطبيع `ی`(U+06CC)→`ي`(U+064A) و`ك`(U+0643)→`ك`(U+064A نسخة عربية) — التقرير أظهر `القضایا` بدل `القضايا`.
   - تنظيف «أونلاين» (ظهر `اونالین` في الاستخراج الخام) عبر قاموس مصطلحات صغير.
   - إسقاط خلايا «العطلة»/الفارغة.
6. المخرجات بـ schema مطابق للمرجع الحالي:
   ```json
   {"day":"السبت","level":"1","group":"1","section":"1","track":"",
    "start":"9:00","end":"10:30",
    "text":"القضايا المجتمعية د/ مصطفى عبدالله اونلاين","page":1}
   ```
   + `students[]` (مستوى/مجموعة أو تخصص/سكشن) + `days[]` + `pages{}`.
7. كتابة `data/meta.json`: `generated_at`, `pdf_sha256`, `events_count`, `source_pages`.

### 4.3 التحقق (الاختبار الذهبي) 🔴
- **الموقع الحالي `scheadel` يحوي نفس الـ PDF ونفس البيانات (1561 محاضرة مدمجة في `const DATA`).**
- نحفظ `tests/fixtures/reference-data.json` (مستخرج من `scheadel`) ونجعل `tests/test_extract.py` يقارن:
  - عدد الأحداث لكل (level, day) · عدد `students` · مجموعات/تخصصات · تطابق `(day,level,group,section,start)` كمجموعة مفاتيح · نسبة تطابق `text` بعد التطبيع.
  - أي اختلاف يُطبع في تقرير للمراجعة اليدوية (مش assert غامض).
- اختبارات وحدة على دوال التطبيع (NFKC/قلب/أرقام) بـ fixtures نصية صغيرة.
- `ci.yml` يشغّل `pytest` على كل push؛ `update.yml` يتوقف لو فشل الاختبار.

### 4.4 المقارنة بين النسخ (`tools/diff_schedule.py`)
- input: `schedule.old.json` + `schedule.new.json` → `diff-report.md` بتقرير: مواد مُضافة/مُحذفة/مُعدَّلة (حسب مفتاح `day+level+group+section+start`) + تغييرات الأوقات/النصوص.
- يُرفق كـ artifact في الـ Action ويُحفظ في `data/history/`.

---

## 5. النشر والأسرار

- 🟡 **GitHub Pages مجاني للريبو الـ PUBLIC فقط** (الخاصة تحتاج خطة مدفوعة) → الريبو يكون public، ولا مشكلة: الجدول عمومي أصلاً والتوكن مش فيه.
- التدفق: `git init -b main` → `git add .` → `git commit` → `gh repo create cs-benha-schedule --public --source . --push` → تفعيل Pages:
  ```
  gh api repos/{owner}/cs-benha-schedule/pages -X POST -f "source[branch]=main" -f "source[path]=/"
  ```
- `.nojekyll` في الجذر.
- `BASE_PATH` في الـ SW/المسارات: الموقع تحت `/cs-benha-schedule/` → كل المسارات نسبية (`./css/style.css`).
- الملفات الكبيرة (الـ PDF في `pdf/`) → Git LFS اختياري، لكن حجم الـ PDF الحالي صغير فيكفي.

---

## 6. مراحل التنفيذ

**المرحلة 1 — الأساس (يتم تنفيذها الآن)**
1. استخراج الـ PDF → `data/schedule.json` + الاختبار الذهبي مقابل reference.
2. بناء الواجهة (HTML/CSS/JS) بالـ palette المعتمد + `print.css`.
3. حفظ الاختيارات في `localStorage` + مشاركة الرابط.
4. `.nojekyll` + `requirements.txt` + `ci.yml`.

**المرحلة 2 — خط التحديث**
5. `update.yml` + `diff_schedule.py` + النشر على GitHub Pages.
6. `sheet_sync.py` + تبويب `overrides` + تطبيقها في الـ Action.
7. فورم الرفع + Apps Script (passcode + Git Data API).

**المرحلة 3 — التحسينات**
8. PWA (`manifest.json` + `sw.js` بـ network-first للبيانات) + أيقونات.
9. تحسينات الوصول/الحركة/`prefers-reduced-motion` + تقرير Lighthouse.

---

## 7. التكلفة

| البند | التكلفة |
|---|---|
| GitHub Pages + Actions (2000 د/شهر) | 0 |
| Google Apps Script | 0 |
| Google Sheets (Shim) | 0 |
| خطوط Cairo self-hosted | 0 |
| **الإجمالي** | **0 جنيه** |

---

## 8. خارج النطاق (YAGNI)

- 🔴 أرقام الجلوس (مش موجودة في الـ PDF — تم استبعادها بقرار Ahmed).
- 🔴 قاعدة بيانات/سيرفر/Node — الموقع ثابت.
- 🔴 Dark mode (الـ palette المطلوب فاتح).
- 🔴 إشعارات/تقويم (ممكن لاحقًا: `.ics` export).

---

## 9. مخاطر معروفة وخطة لها

| الخطر | المعالجة |
|---|---|
| الـ PDF الجديد يتغير تخطيطه | فحص الـ grid في بداية الاستخراج + فشل صريح بدل بيانات خاطئة |
| نص عربي خاطئ (عكس أرقام/حروف) | اختبار ذهبي + قاموس مصطلحات + تقرير اختلافات |
| PWA يخزّن جدول قديم | network-first لـ `schedule.json` + تغيير `CACHE_VERSION` كل نشر |
| فورم الرفع مفتوح | passcode + تحقق حجم/نوع + rate-limit |
| توكن مكشوف | PAT في Script Properties فقط، `.gitignore` لملفات الأسرار |
