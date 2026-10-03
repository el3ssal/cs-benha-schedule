# خطة تنفيذ — cs-benha-schedule

- **التاريخ:** 2026-10-03
- **المرجع:** `docs/superpowers/specs/2026-10-03-cs-benha-schedule-design.md`
- **الأمر الحالي:** Phase 1 فقط (يُنفَّذ فوراً) — Phase 2/3 بانتظار اكتمال 1 وموافقة Ahmed.

> ## ⚠️ مراجعة كبيرة (Session 2 — 2026-10-03): إلغاء تحليل الـ PDF
> **قرار Ahmed:** إيقاف كل عمل `pdfplumber`/`extract_schedule.py`. مصدر البيانات =
> `const DATA` من `scheadel` index.html (موجود أصلاً في `tests/fixtures/reference-data.json` — 1561 حدث / 137 طالب).
> خط التحديث المستقبلي: PDF جديد → **ChatGPT** يحلله بـ **PROMPT A** (في `docs/PROMPTS.md`) →
> Ahmed يلزّق النتيجة للـ agent بـ **PROMPT B** → Validate/Import/Diff/Tests → موافقة على commit.
> النتائج: **T1/T2 مُصاغان من جديد أدناه** · مفتاح الـ diff صار يشمل `track` (T3/T4) · T9 بسيط بدون استخراج في CI.
> تفاصيل ما تم/المتبقي: `docs/HANDOFF.md` (يُقرأ أولاً).

**قاعدة عامة:** كل مهمة ليها *تحقق* (verification) لازم يتنفّذ قبل ما ننتقل. أي مهمة بتفشل التحقق → نتوقف ونراجع Ahmed.

---

## المرحلة 1 — الأساس

### T0 · تجهيز الريبو (بدون commit لحد ما Ahmed يأذن)
- **ملفات:** `pdf/جدول-العام.pdf` (نسخ من `C:\Users\ahmed\Desktop\coll\`) · `.gitignore` · `.nojekyll` · `tools/requirements.txt` · `requirements-dev.txt` · `README.md`
- **خطوات:**
  1. نسخ الـ PDF (أصله يفضل في مكانه — Copy Before Overhaul).
  2. `.gitignore`: `.env`, `service-account*.json`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/`.
  3. `requirements.txt`: `pdfplumber==0.11.*`, `pypdf==6.*` · dev: `pytest`.
  4. `git init -b main` + `git config user.name/email` محلي (هوية `Ahmed El3ssal <ahmedel3ssal1@gmail.com>`) — **لا commit بدون إذن Ahmed**.
- **تحقق:** `Test-Path pdf/*.pdf` ✅ · `python -m pip install -r tools/requirements.txt` ينجح.

### T1 (revised) · استيراد البيانات → `data/schedule.json` — بدون أي تحليل PDF
- **ملفات:** `tools/import_schedule.py` · (ملف المصدر الأول: `tests/fixtures/reference-data.json` = `const DATA` من scheadel)
- **خطوات:**
  1. `load_payload(path)` → dict (يتقبل payload ChatGPT أو الـ fixture).
  2. `validate(payload)` → `(errors, warnings, fixes)` بالترتيب:
     - top-level keys = `days, events, students, pages` (مفاتيح إضافية زي `issues`/`summary` تُبلَّغ ولا تُكتب في schedule.json)؛
     - `days` = الأسماء الستة بالترتيب؛ `pages` مفاتيحها أعداد متتالية من `"1"`؛ لكل حدث `event.day == pages[str(event.page)]`؛
     - `level` ∈ `"1".."4"`؛ L1/L2: `track==""` و`group` digit-string؛ L3/L4: `track` ∈ الـ 4 المسموحات و`group == null` في events و `== ""` في students (عدم تناظر مقصود — تُحافظ عليه كما هو)؛
     - `start/end`: شبكة الـ 45 دقيقة 9:00..18:00، بدون leading zero (`9:00` مش `09:00`)، `end > start`؛
     - `text`: غير فارغ، لا `ی`/`ک` فارسية، لا أرقام مقلوبة، لا نص معاكس؛
     - **لا توكر** في المفتاح `(day, level, group, track, section, start)` — **`track` إلزامي في المفتاح** (من غيره 129 توكر كاذب في المرجع)؛
     - كل قسم في events موجود في `students`.
  3. `auto_fix` للفقري فقط: مسافات، `ی→ي`/`ک→ك`، إزالة leading zero في الوقت. أي مشكلة معنى → **إيقاف وسؤال Ahmed**.
  4. CLI: `python tools/import_schedule.py <payload> --out data/schedule.json --meta data/meta.json` → يكتب `meta.json` {`generated_at`, `payload_sha256`, `events_count`, `students_count`, `source`} + يطبع تقرير fixes/warnings.
  5. **أول تشغيل:** المصدر = `tests/fixtures/reference-data.json` → `data/schedule.json` + `data/meta.json`.
  6. اصطلاح المستقبل: payloads تُحفظ في `data/inbox/schedule-YYYY-MM-DD.json` (تُark_commit للتاريخ).
- **تحقق:** `python tools/import_schedule.py tests/fixtures/reference-data.json --out data/schedule.json` بلا أخطاء · `len(events)==1561` و`len(students)==137` · الـ output **مطابق 100%** للمرجع (يدخل في T2).

### T2 (revised) · اختبارات pytest — بوابة الجودة 🔴
- **ملفات:** `tests/test_schedule.py` · `tests/test_import.py`
- **خطوات:**
  1. `test_schedule.py::test_matches_reference` — `data/schedule.json` يطابق `tests/fixtures/reference-data.json` **مطابقة تامة (100%)** (نفس البيانات مُستوردة منه — أي فرق = bug في الـ import). (اختبار الـ ≥95% نصي **ملغى** — لا يوجد استخراج PDF.)
  2. `test_schedule.py::test_schema_consistency` — نفس قواعد validate (تُعاد استخدامها على أي import مستقبلي): enum days/levels/tracks، شبكة الأوقات، توكر المفتاح مع `track`، `event.day==pages[...]`، `group null/""`، الأقسام ∈ students.
  3. `test_import.py` — وحدات للـ validator: track غلط = error · وقت خارج الشبكة = error · توكر (مع/بدون track) = error · قسم ناقص في students = error · `09:00→9:00` fix · `ی→ي` fix · مفتاح ناقص = error · ملاحظات إضافية (`issues`) لا تُكتب في schedule.json.
  4. `python -m pytest -q` = **أخضر 100%**.
- **تحقق:** بوابة الخطة — بدون أخضر: لا T3 ولا واجهة ولا نشر. لو أي فشل → وقف واعرض التقرير على Ahmed.

### T3 · تطبيق الـ overrides
- **ملفات:** `tools/apply_overrides.py` · `data/overrides.json` (فارغ في البداية) · schema زي ما في الـ spec §2.3 **مع تعديل وحيد: الـ `key` يشمل `track`** → `{"day","level","group","track","section","start"}` (بدونه الـ L3/L4 غامض لأن الأقسام تبدأ من 1 في كل track).
- **تحقق:** اختبارات وحدة: `update` يعدّل خلية · `delete` يشيل حدث · `add` يضيف حدث جديد · override على مفتاح غير موجود → خطأ واضح.

### T4 · أداة المقارنة
- **ملفات:** `tools/diff_schedule.py` · `tests/test_diff.py`
- **التعديل:** المفتاح = `day+level+group+track+section+start` (أُضيف `track` — انظر مراجعة أعلى).
- **تحقق:** نسختين اصطناعيتين → تقرير `added/removed/changed` صحيح.

### T5 · الواجهة (HTML + design tokens)
- **ملفات:** `index.html` · `css/style.css` · `fonts/` (Cairo subset woff2) · `icons/`
- **خطوات:** tokens زي الـ spec §3.1 · RTL `dir=rtl lang=ar` · header + شريط الاختيار + كارت اليوم + شبكة الأسبوع + toggle + فوتر + أزرار (طباعة/مشاركة/تحديث) + حالات loading/error/empty.
- **تحقق:** فتح `index.html` محلي (سيرفر: `python -m http.server 8000`) — المحتوى يبان، `prefers-reduced-motion` محترم، focus rings ظاهرة.

### T6 · منطق التطبيق
- **ملفات:** `js/app.js` · `js/data.js`
- **خطوات:** تحميل `data/schedule.json` + تحقق schema · ربط 3 selects (المستوى → المجموعة/التخصص → السكشن) · `localStorage` للاختيارات · قراءة/كتابة `?level=&cat=&section=` · رندر "مواعيد اليوم" (بحسب `new Date()` + `days[]`) و"باقي الأسبوع" · escapeHtml لكل النصوص.
- **تحقق:** يدوي عبر `agent-browser`: اختيار مستوى 1 → مجموعة 1 → سكشن 1 → يظهر حدث «القضايا المجتمعية … 09:00 - 10:30» · إعادة تحميل → الاختيار محفوظ · مشاركة الرابط → نفس الحالة.

### T7 · الطباعة
- **ملفات:** `css/print.css`
- **تحقق:** `agent-browser eval` يشغّل `window.print()`/المعاينة → الأزرار مخفية والجدول كامل، بدون قصّ في الصفحة.

### T8 · CI الأساسي
- **ملفات:** `.github/workflows/ci.yml`
- **خطوات:** على كل push → تثبيت requirements → `pytest`.
- **تحقق:** يتنفّذ بعد إنشاء الريبو (T10) — نشوفه أخضر.

---

## المرحلة 2 — خط التحديث (بانتظار اكتمال 1)

- **T9 · `update.yml`** (بعد المراجعة — **لا استخراج PDF في الـ CI**): trigger على `data/**` → تثبيت `tools/requirements.txt` → `pytest` (يفشل؟ يتوقف النشر) → تطبيق `overrides` من الشيت (T11) → `diff_schedule.py` بالنسخة السابقة → `diff-report.md` (artifact) → deploy Pages. الاستخراج يحدث **خارج** الـ CI (ChatGPT + PROMPT B → الم agent يعمل commit لـ `data/schedule.json`).
- **T10 · النشر**: `gh repo create cs-benha-schedule --public --source . --push` → تفعيل Pages API → إضافة `.nojekyll` → التحقق من `https://el3ssal.github.io/cs-benha-schedule/`.
  - ⚠️ يحتاج إذن Ahmed + تأكيد إن الريبو يكون **public** (Pages مجاني للعام فقط).
- **T11 · Google Sheets**: إنشاء الشيت `cs-benha-schedule` بتبويبين (`mirror`, `overrides`) + service account + Secrets في GitHub (`GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_ID`) + `tools/sheet_sync.py`.
  - ⚠️ يحتاج من Ahmed: مشاركة الشيت على إيميل الخدمة بصلاحية Editor.
- **T12 · فورم الرفع**: `<form>` في الموقع + Apps Script web app (passcode SHA-256، تحقق حجم/نوع، Git Data API، rate-limit) → يبني commit يشغّل الـ Action.
  - ⚠️ يحتاج من Ahmed: إنشاء المشروع في script.google.com + نشر `deploy web app` + سرّ الـ PAT.

---

## المرحلة 3 — التحسينات (بعد 1 و2)

- **T13 · PWA**: `manifest.json` + `sw.js` في الجذر — **cache-first للـ shell، network-first مع fallback لـ `schedule.json`، و`CACHE_VERSION` يتحدّث كل نشر** + أيقونات 192/512.
- **T14 · الوصول والأداء**: Lighthouse (accessibility ≥90) · `aria-live` · `theme-color` · OG image.
- **T15 · التوثيق**: `README.md` (خطوات التحديث بالـ PDF + بالشيت + بالفورم).

---

## ترتيب الاعتماد

```
T0 → T1 → T2 ─┐
T0 → T3 ──────┼→ T5 → T6 → T7 → (T8,T10) → T9 → T11 → T12 → T13 → T14 → T15
T4 (مستقل) ───┘
```
T2 هو **بوابة الجودة**: من غير أخضر، مفيش واجهة، مفيش نشر.

## نقاط توقف تتطلب Ahmed
1. قبل أي `git commit` / `git push` / إنشاء ريبو (أعطيه صياغة الـ commit).
2. لو التطابق مع المرجع <95%.
3. قبل إنشاء service account / Apps Script (بيانات اعتماد).
