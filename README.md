# جدول محاضرات حاسبات بنها (cs-benha-schedule)

موقع ثابت مستقل (Vanilla HTML + CSS + JS، بدون build) يعرض جدول محاضرات كلية
الحاسبات والذكاء الاصطناعي — جامعة بنها، بالعربية (RTL) وpalette فاتح.
البيانات من `data/schedule.json` (المصدر: `const DATA` من موقع scheadel).

## تشغيل محلي

```powershell
python -m http.server 8000
# ثم افتح http://127.0.0.1:8000/
```

## الاختبارات

```powershell
pip install -r requirements-dev.txt
python -m pytest -q   # بوابة الجودة — يجب أن تكون خضراء 100%
```

## تحديث الجدول (PDF جديد)

لا يوجد تحليل PDF داخل المشروع. المسار الرسمي (`docs/PROMPTS.md`):

1. ارفع الـ PDF الجديد على ChatGPT مع **PROMPT A** → يعيد JSON كاملاً + SELF-CHECK.
2. الصق النتيجة مع **PROMPT B** → تُحفظ في `data/inbox/schedule-YYYY-MM-DD.json`،
   تُتحقق عبر `tools/import_schedule.py`، تُقارن عبر `tools/diff_schedule.py`،
   ثم تُكتب `data/schedule.json` + `data/meta.json` بعد `pytest` أخضر.
3. الـ commit (بعد الموافقة على رسالته) يشغّل `update.yml`: pytest ← تطبيق
   `data/overrides.json` ← تقرير `diff-report.md` ← نشر GitHub Pages.

```powershell
python tools/import_schedule.py data/inbox/schedule-2026-10-03.json --out data/schedule.json --meta data/meta.json
python tools/apply_overrides.py data/schedule.json --overrides data/overrides.json --out data/schedule.json
python tools/diff_schedule.py old.json data/schedule.json --out diff-report.md
```

## تعديلات يدوية (overrides)

`data/overrides.json` فوق ناتج الاستيراد (`update`/`delete`/`add` بمفتاح
`day+level+group+track+section+start` — `track` إلزامي). أي مفتاح مجهول = خطأ
صريح يوقف النشر.

### Google Sheets (T11)

1. أنشئ شيت `cs-benha-schedule` بتبويبين فارغين: `mirror` و`overrides`.
2. أنشئ service account وشارك الشيت مع إيميله بصلاحية **Editor**.
3. ضع في GitHub Secrets: `GOOGLE_SERVICE_ACCOUNT_JSON` (محتوى JSON) و`SHEET_ID`.
4. المزامنة: `python tools/sheet_sync.py --sheet-id <ID> --overrides-out data/overrides.json`
   (تكتب `mirror` من الجدول الحالي وتسحب `overrides` — الأعمدة في docstring الملف).
   خطوة `update.yml` تعمل تلقائياً عند وجود `SHEET_ID` فقط.

## فورم الرفع من الموقع (T12)

الكود المرجعي في `gas/Code.gs` — انشره أنت من `script.google.com`:

1. مشروع جديد → الصق الملف → فعّل Script Properties (server-side فقط):
   `PASSCODE_HASH` = `hex(SHA-256(passcode))`، و`GITHUB_PAT` (صلاحية
   contents:write على هذا الريبو فقط)، و`GITHUB_REPO` و`GITHUB_BRANCH` و`PDF_PATH`.
2. Deploy → Web app → Execute as: Me → Access: Anyone → انسخ رابط `/exec`.
3. أي commit عبر الـ PAT يشغّل `update.yml` تلقائياً (عكس `GITHUB_TOKEN`).

## PWA

`sw.js` في الجذر: cache-first للواجهة، network-first مع fallback لبيانات
الجدول. **عند كل نشر يغيّر ملفات الواجهة: ارفع `CACHE_VERSION` في `sw.js`**
وإلا رأى الطلاب نسخة قديمة مخزنة.

## النشر (T10 — يحتاج موافقة)

الريبو يجب أن يكون **PUBLIC** (Pages المجاني للعام فقط):

```powershell
git init -b main
git add .
git commit -m "<رسالة تُطلب من أحمد أولاً>"
C:\Program` Files\GitHub` CLI\gh.exe repo create cs-benha-schedule --public --source . --push
```

## المتبقي (خطوات يدوية من أحمد فقط — الكود جاهز)

- T11: إنشاء الـ Sheet ومشاركته مع إيميل الـ service account (الكود `tools/sheet_sync.py` جاهز ومُختبَر).
- T12: لصق `gas/Code.gs` ونشر الـ web app + تعبئة الـ Secrets (الكود جاهز).
