# PROMPTS — سير عمل تحديث الجدول (ChatGPT + opencode)

> هذه الملف هي المرجع الرسمي لـ schema بيانات الجدول. يُستخدم في مسار التحديث:
> **PDF جديد → ChatGPT (PROMPT A) → Ahmed يلزّق النتيجة مع PROMPT B للمعين → Validate/Import/Diff/Tests → موافقة على commit → نشر.**
> لا يوجد أي تحليل PDF داخل المشروع — `pdfplumber` ملغى عملياً (انظر `docs/HANDOFF.md` §4 banner).

---

## PROMPT A — يُرفع مع الـ PDF الجديد على ChatGPT

```text
ROLE
You are a precise data-extraction engine. Attached is a NEW version of an Arabic university lecture timetable PDF: Benha University, Faculty of Computer Science & Artificial Intelligence. Layout: 4 levels, 6 days, one giant table split across consecutive pages, 12 daily periods of 45 minutes (period 1 starts 09:00, period 12 ends 18:00).

GOAL
Extract EVERY lecture cell from ALL pages into ONE JSON object with exactly the schema below, then run the self-check and report the results.

OUTPUT FORMAT — exactly two parts:
1. ONE ```json code block containing the JSON object (no prose before it).
2. A "SELF-CHECK" section AFTER the code block with counts and any ISSUES.

JSON SCHEMA
{
  "days": ["السبت","الأحد","الإثنين","الثلاثاء","الأربعاء","الخميس"],
  "events": [
    {"day":"السبت","level":"1","group":"1","section":"1","track":"","start":"9:00","end":"10:30","text":"القضايا المجتمعية د/ مصطفى عبدالله اونلاين","page":1}
  ],
  "students": [
    {"level":"1","group":"1","track":"","section":"1"}
  ],
  "pages": {"1":"السبت","2":"السبت","3":"السبت"}
}

STRICT RULES
1. level: "1" | "2" | "3" | "4" (string). group/section: digit strings ("1", "10").
2. Levels 1-2: group = "1".."7", track = "" (empty string).
   Levels 3-4: group = JSON null in events AND "" in students; track = one of exactly:
   "حسابات علمية" | "ذكاء اصطناعى" | "علوم حاسب" | "نظم معلومات".
3. Section numbering: levels 1-2 are numbered GLOBALLY per level (previous version: L1 = 1..50, L2 = 1..40); levels 3-4 RESTART at 1 for each track.
4. start/end: 24-hour, NO leading zero ("9:00","12:45","16:30","18:00"), on this grid only:
   9:00 9:45 10:30 11:15 12:00 12:45 13:30 14:15 15:00 15:45 16:30 17:15 (end = start + 45 or more; last period ends 18:00). Typical lecture = 2 periods (90 min).
5. text = the cell content in CORRECT Arabic reading order (never mirrored), single spaces; convert Persian ی (U+06CC) -> ي and ک (U+06A9) -> ك; digits exactly as displayed ("14" must never become "41"); keep instructor prefixes (د/ م/) and hall/online info. One cell = ONE event (join multi-line cell text with single spaces).
6. pages = EVERY page number as a string key ("1".."N") mapped to its day, read from the day header of each day block. Day blocks are consecutive pages in this order: السبت، الأحد، الإثنين، الثلاثاء، الأربعاء، الخميس. Every event's page must agree with pages.
7. students = one entry per section ROW that exists in the timetable (every row with a section number), not per event. Expect the same order of magnitude as the previous version: 1561 events / 137 students — a big drop means you missed pages; investigate before answering.
8. Skip empty cells, break/rest cells and holiday cells (العطلة / تعطيل).

PDF LAYOUT HINTS (verify, do not assume)
- rows = sections; label columns sit at the RIGHT edge of the table: [section number] [group-or-track] [sometimes junk] [level].
- labels are vertically merged: day / level / group / track labels are printed ONLY on the first row (or first page) of their scope — carry each value forward until the next label appears.
- the day name appears only on the first page of each day block.
- L1/L2 rows may show junk in label columns ("رياضة علمى", "علوم علمى") — ignore it.
- labels can be clipped in the source: a lone "المجموعة" without an ordinal that STARTS A NEW GROUP = previous group number + 1; a clipped track/level fragment (e.g. "ال") = carry the previous value forward.
- ignore header rows (period numbers + the two time rows).

SELF-CHECK (report after the JSON)
- counts: total events; events per level; distinct students per level; number of pages.
- every event.page exists in pages and matches its day.
- all times on the grid; end > start; no duplicate (day, level, group, track, section, start).
- Arabic quality: no mirrored text, no reversed digits, no Persian ی/ک.
- "ISSUES: page N / section X — problem — assumption" for anything illegible.

COMPLETENESS: scan all pages one by one before answering. Do NOT summarize or sample — output the full data.
```

---

## PROMPT B — يُلزّق به Ahmed للـ agent (opencode) مع البيانات الجديدة

```text
New timetable data extracted by ChatGPT from the updated PDF is below (schema = "PROMPT A" in docs/PROMPTS.md). Process it end-to-end.

< PASTE THE JSON PAYLOAD HERE >

GLOBAL RULES (unchanged): reply in Arabic (technical terms in English); NEVER git commit/push without asking me for the exact commit message and getting my approval first; NEVER install new dependencies; do not touch .env/config files.

STEPS
1. Save the payload verbatim to data/inbox/schedule-YYYY-MM-DD.json.
2. Validate it (tools/import_schedule.py + tests):
   - top-level keys: days, events, students, pages (extra keys like "issues"/"summary" are allowed but must be reported separately, not written to schedule.json);
   - days = the 6 fixed names in order; pages keys are consecutive integers from "1"; for every event: event.day == pages[str(event.page)];
   - level in "1".."4"; L1/L2: track == "" and group is a digit string; L3/L4: track in the 4 allowed values, group == null in events / "" in students;
   - start/end on the 45-min grid 9:00..18:00, no leading zero, end > start;
   - text non-empty, no Persian ی/ک, no reversed digits, no mirrored Arabic;
   - no duplicate (day, level, group, track, section, start) keys;
   - every event's section exists in students.
   Auto-fix ONLY mechanical issues (whitespace, ی/ک, leading zeros, "09:00" -> "9:00"). Semantic issues -> STOP and ask me.
3. Compare with the current data/schedule.json: totals, per-level and per-day counts, plus a diff keyed on (day, level, group, track, section, start) -> write data/diff-report.md with added / removed / changed. If data/schedule.json does not exist yet, skip the diff.
4. If validation passes: write data/schedule.json + data/meta.json {generated_at, payload_sha256, events_count, students_count, source: "chatgpt-import"}.
5. Run pytest — must be green. On any failure: stop and show me the failures.
6. Reply with a concise Arabic summary: counts, diff highlights, anything auto-fixed, anything suspicious — plus a SUGGESTED COMMIT MESSAGE — then WAIT for my explicit approval before committing.
```
