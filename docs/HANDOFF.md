# HANDOFF — cs-benha-schedule (Benha CS lecture schedule site)

> **Purpose of this file:** continue a paused session seamlessly. Read this first, then the spec and plan below. Everything you need to know — what is DONE, what is LEFT, and the exact technical findings — is here.
> **Session 1 paused:** 2026-10-03 (context limit). Arabic PDF extraction research was in progress.
> **Session 2 paused:** 2026-10-03 (context limit). **⏸️ MAJOR: PDF parsing ABANDONED by Ahmed's decision — data now comes from scheadel's `const DATA`; future PDF updates are analyzed by ChatGPT (see `docs/PROMPTS.md`).** Session 2 resolved both open issues, proved schema facts, and rewrote T1/T2 in the plan.
> **Session 3 done:** 2026-10-03 — T1 (import) + T2 (29 pytest green) + T3 (overrides) + T4 (diff) + T5/T6/T7 (UI, verified in-browser) + T8/T9 (CI/update workflows) + T13 (PWA) + T15 (README). **No git repo yet, NO commits.**
> **Session 4 done:** 2026-10-03 — Ahmed approved everything: T0 (`git init`, local identity) + first commit `1fae765` + T10 (**PUBLIC** repo `el3ssal/cs-benha-schedule`, pushed, Pages live at `https://el3ssal.github.io/cs-benha-schedule/`) + T11 code (`tools/sheet_sync.py`, `gspread` installed approved, 8 parser tests) + T12 code (`gas/Code.gs`) + fixed `update.yml` (`secrets`→`env` in `if`, +`workflow_dispatch`) — update.yml run green, diff artifact OK. Total **37 pytest passed**.
> **➡️ NEXT: manual steps only Ahmed can do — create the Google Sheet + share with the service-account email as Editor (+ set `SHEET_ID`/`GOOGLE_SERVICE_ACCOUNT_JSON` secrets); paste `gas/Code.gs` in script.google.com + deploy web app (+ PAT in Script Properties). Plan file T1/T2/T3/T4/T9 notes still authoritative.**

---

## 0. Project goal

Rebuild `https://cs-benha-schedule.floot.app/` (a Floot wrapper that iframes `https://ahmedawadfathy.github.io/scheadel/`) as a **standalone, minimal/modern, light-palette Arabic (RTL) static site** that:
1. Reads its data from `data/schedule.json` generated from the faculty PDF timetable.
2. Can be updated any time by **dropping a new PDF** (git push), **editing a Google Sheet** (overrides), or **uploading the PDF through a form on the site**.
3. Ships: saved selections (localStorage), export/print, PWA + offline, diff between schedule versions.

**Approved decisions (asked & answered by Ahmed):**
| Topic | Decision |
|---|---|
| Stack | **Vanilla HTML + CSS + JS** (no framework, no build step) |
| Hosting | **GitHub Pages** (⚠️ requires **PUBLIC** repo — free Pages) |
| Source of truth | **PDF** → `schedule.json` |
| Google Sheets role | **Override/edit layer on top of the PDF extract** (`overrides` tab) |
| Update entrances | **Both**: git push of PDF **and** on-site upload form (via Google Apps Script, token hidden in Script Properties) |
| Features to include | localStorage selections, export/print, PWA+offline, version diff |
| **Seat numbers** | **REMOVED from scope** (not present in PDF — verified) |
| Palette | warm white `#FAFAF8` + blue `#2563EB` (approved "موصى به") |
| Approach | A + Google Sheets |

---

## 1. Reference documents (READ THESE NEXT)

| File | Content |
|---|---|
| `docs/superpowers/specs/2026-10-03-cs-benha-schedule-design.md` | **Approved spec** — 9 sections: repo structure, 3 update entrances + security, UI/tokens, extraction algorithm, deployment+secrets, 3 phases, cost (0 EGP), out-of-scope, risk table |
| `docs/superpowers/plans/2026-10-03-cs-benha-schedule-plan.md` | **Implementation plan** — tasks T0…T15 with per-task verification gates, dependency graph, and "stop & ask Ahmed" points. **T1/T2/T3/T4/T9 REVISED in session 2 (plan now authoritative for remaining steps)** |
| `docs/PROMPTS.md` | **NEW (session 2)** — PROMPT A (ChatGPT analyzes the new PDF) + PROMPT B (Ahmed pastes the payload to the agent) + the official data schema |

---

## 2. WORKING DIRECTORY / ENVIRONMENT

```
Project root : C:\Users\ahmed\Desktop\coll\cs-benha-schedule\
Original PDF : C:\Users\ahmed\Desktop\coll\جدول العام (1)-1.pdf   (do not delete — Copy Before Overhaul)
Copied PDF   : C:\Users\ahmed\Desktop\coll\cs-benha-schedule\pdf\جدول-العام.pdf  (188,426 bytes, 33 pages)
Python       : 3.14.3  (installed & approved: pdfplumber==0.11.10, pypdf==6.19.0 — no other deps installed yet)
OS/Shell     : Windows, PowerShell 7 (pwsh) — use `workdir` param, avoid `cd`; Arabic in console may show as `?` (encoding only)
Reference    : tests/fixtures/reference-data.json   ← extracted `const DATA` from scheadel (see §5)
```

**No git repo has been initialized yet.** (T0 half-done — see §3.)

---

## 3. DONE SO FAR ✅

1. ✅ Explored live site: Floot page = wrapper + `<iframe src="https://ahmedawadfathy.github.io/scheadel/">`.
2. ✅ Fetched & analysed `scheadel` HTML: single self-contained file, `const DATA` = **1561 events, 137 students, 6 days, 33 pages**, no fetch, no localStorage, **no upload feature** (footer text lies).
3. ✅ Installed & approved `pdfplumber` + `pypdf`.
4. ✅ Verified PDF has **no seat numbers** (no 6+ digit numbers in any of 33 pages).
5. ✅ Clarifying questions → all decisions in §0 table.
6. ✅ **Spec written & self-reviewed** → `docs/superpowers/specs/2026-10-03-cs-benha-schedule-design.md`.
7. ✅ **Plan written** → `docs/superpowers/plans/2026-10-03-cs-benha-schedule-plan.md`.
8. ✅ **T0 partial**: created `.gitignore`, `.nojekyll` (empty), `tools/requirements.txt`, `requirements-dev.txt`, copied PDF to `pdf/`.
9. ✅ **Reference fixture extracted** → `tests/fixtures/reference-data.json` (regex `const DATA\s*=\s*(\{.*?\})\s*;\s*\n` on the saved scheadel HTML at `C:\Users\ahmed\.local\share\opencode\tool-output\tool_102f8e3880014gX1VEIPpAx8E1`).
10. ✅ **Deep PDF structure reverse-engineering** → all findings in §4 (this is the expensive knowledge — do not re-derive it).

### Session 2 (2026-10-03) ✅
11. ✅ Re-verified environment: Python 3.14.3 · pdfplumber 0.11.10 · pypdf 6.19.0 · fixture schema (keys `days/events/students/pages`, event keys, student keys, day names, `pages{}` map).
12. ✅ **Dumped page 1 rows (82 rows)** — header rows identified: row0 = period numbers `12…1`, row1 = period START times (`09:00` rightmost… `05:15` leftmost = 17:15), row2 = period END times. Label columns confirmed; group boundaries of L1 (labels at sections 1/8/15/22/29/37/44) and L2 (1/7/13/20/27) **exactly match the reference → OPEN ISSUE 2 resolved: there is NO off-by-one** (the confusion was row-index vs section-number).
13. ✅ **Char-level analysis**: page1 row79 label is genuinely truncated to `المجموعة` (ordinal `الخامسة` is NOT drawn — clipped by the source; text sits at the cell's bottom edge). Page2 row0 carries the full `المجموعة الخامسة` at section 30 → a lone `المجموعة` starting a new group = **previous group + 1** (not inherit).
14. ✅ **Dumped pages 2/8/9 + full 33-page anomaly scan (50 anomalies, all categorized)** → **OPEN ISSUE 1 resolved**: page 8 row16 has level label `الرابع لمستوى` (match on substring `مستوى`, NOT `المستوى` — the PDF renders `لمستوى`); page 9 level cell = fragment `ال` → ignore + forward-fill (from page 8) works. Track fragments: P8 r0 `معلومات` (clipped `نظم معلومات`), P9 r0 empty (forward-fill from P8 r23) — both resolvable by forward-fill. Remaining anomaly types: junk column (`رياضة علمر`/`علوم علمى`), empty label cells, P2 r29 empty track label. **All moot for production now (parsing abandoned), but kept as knowledge in §4.**
15. ✅ **Schema facts proven against the reference (CRITICAL for prompts/tests — see §4.10)**: unique key MUST include `track` (else 129 false duplicates); `events[].group = null` for L3/L4 while `students[].group = ""` (intentional asymmetry — preserve); students ↔ events are 1:1 (137 = 137, every section has ≥1 event).
16. ✅ **STRATEGY CHANGE (Ahmed's decision):** abandon `pdfplumber` extraction entirely. Source of truth now = scheadel's `const DATA` (already saved as `tests/fixtures/reference-data.json`). Future updates: new PDF → **ChatGPT with PROMPT A** → Ahmed pastes payload + **PROMPT B** to the agent → validate/import/diff/test → approved commit.
17. ✅ **`docs/PROMPTS.md` written** — PROMPT A + PROMPT B (copy-paste ready, English).
18. ✅ **Plan revised** — T1/T2 rewritten (import + pytest instead of extraction + 95% golden), T3/T4 keys now include `track`, T9 simplified (no extraction in CI). **Nothing else was modified; NO git repo yet; NO commits.**

### Session 3 (2026-10-03) ✅
19. ✅ **T1**: `tools/import_schedule.py` (stdlib only) — first import from `tests/fixtures/reference-data.json` → `data/schedule.json` + `data/meta.json`, 1561/137, 0 fixes, parsed output 100% identical to reference.
20. ✅ **T2**: `tests/test_schedule.py` (golden + consistency + meta) + `tests/test_import.py` (14 validator units); installed `pytest==8.*` from `requirements-dev.txt` (Ahmed approved, no new libs); `pytest -q` green.
21. ✅ **T3**: `tools/apply_overrides.py` (update/delete/add, unknown key = hard error, re-validates result) + `data/overrides.json` (`{"overrides": []}`) + `tests/test_overrides.py` (8 tests).
22. ✅ **T4**: `tools/diff_schedule.py` → Arabic `diff-report.md` (added/removed/changed on the 6-field key incl. `track`) + `tests/test_diff.py` (4 tests). Total **29 passed**.
23. ✅ **T5/T6/T7**: `index.html` + `css/style.css` (tokens, pills-desktop/selects-mobile, today card, week grid, toggle, dialog, skeleton/error/empty states, `aria-live`, skip link, reduced-motion) + `js/data.js` + `js/app.js` (snake_case, 3 dependent selects, localStorage `cs_benha_schedule_selection_v1`, `?level=&cat=&section=`, `escapeHtml`, share/print) + `css/print.css` — Cairo subsets self-hosted in `fonts/` (4×~30KB). Verified in-browser: L1/1/1 → `القضايا المجتمعية 9:00 - 10:30`, reload persists, shared URL restores (incl. L3 track), 0 console errors, PDF-print path works.
24. ✅ **T8/T9**: `.github/workflows/ci.yml` (pytest on push) + `update.yml` (trigger `data/**`: pytest gate → apply overrides → diff artifact → Pages deploy).
25. ✅ **T13/T15**: `manifest.json` + `sw.js` at root (cache-first shell, network-first `schedule.json`, `CACHE_VERSION="v1"`) + Pillow-generated `icons/` + `README.md` (Arabic, update flow, deploy) + `data/inbox/.gitkeep`.

---

## 4. PDF STRUCTURE — EXACT FINDINGS (do not re-research)

> ### ⏸️ HISTORICAL — PDF parsing was ABANDONED in session 2
> Ahmed's decision: **do NOT write `extract_schedule.py` / `textnorm.py` and do NOT run pdfplumber again.** Data comes from `tests/fixtures/reference-data.json` (= scheadel `const DATA`); future PDFs go through ChatGPT (`docs/PROMPTS.md` PROMPT A). This section is kept only as background knowledge (some rules were copied into PROMPT A).

### 4.1 Geometry
- 33 pages, 841×595 pt (A4 landscape).
- One giant logical table split across pages; `page.find_tables()` returns **1 table/page** (sometimes column count differs: 14/15/16 — because pdfplumber merges adjacent columns when a divider line is missing. **Do NOT use `len(table.columns)` for classification — use cell x-coordinates.**)
- **Period grid (12 columns, 45 min each):** left edge `x = 50.21`, right edge of period area `x = 721.43` → column width ≈ **55.94** (i.e. `x0 ≈ 50.21 + 55.94 * i`, i = 0…11).
  - Column i=0 (leftmost) = **period 12**, i=11 (rightmost) = **period 1**.
- **Label columns** (x ≥ 721.43):
  - `x≈721.4–738.5` → **section number** (digits)
  - `x≈738.5–757.1` → **group** (L1/L2) *or* **track/specialization** (L3/L4)
  - `x≈757.1–774.1` → **level** (when track col is used) *or* junk 4th column for L1/L2 (see 4.5)
  - `x≈774.1–790.8` → **level** (when 4 label columns exist)
  - A cell starting at `x≈738` spanning to `≈791` on the **first row of a day** = **day name** (e.g. `السبت`, `الأحد`…)
- ⚠️ Cells can be **merged horizontally** (a lecture = 2 periods = 112pt wide cell) and **vertically** (labels span several rows). `row.cells[i]` = bbox tuple or `None` (merged).

### 4.2 Row semantics
- Rows = **sections** (each row has a number in the `x≈721` column). Header rows (period numbers + two time rows) come first on the first page of the PDF only.
- **Labels are forward-fill**: a label cell appears only on the FIRST row of its scope; state carries down until a new label appears.
- Day label appears only on the **first page of each day block** → forward-fill across pages inside the block; **reset on new day label**.

### 4.3 Day blocks (verified)
```
السبت   pages 1–3
الأحد    pages 4–9
الإثنين  pages 10–15
الثلاثاء  pages 16–21
الأربعاء  pages 22–27
الخميس   pages 28–33
```
Also available as `reference-data.json → pages{}` (page# → day) for validation only (production must derive from the PDF).

### 4.4 Ground truth for validation (from `reference-data.json`)
- **Level → pages:**
  - L1: `1,4,5,10,11,16,17,22,23,28,29`
  - L2: `2,6,7,12,13,18,19,24,25,30,31`
  - L3: `2,3,7,8,13,14,19,20,25,26,32`
  - L4: `3,8,9,14,15,20,21,26,27,32,33`
  (⇒ **levels change mid-page**; forward-fill is mandatory.)
- **Section numbering:**
  - L1: **global per level** — group1 `1–7`, group2 `8–14`, group3 `15–21`, group4 `22–28`, group5 `29–36`, group6 `37–43`, group7 `44–50`
  - L2: **global per level** — group1 `1–6`, g2 `7–12`, g3 `13–19`, g4 `20–26`, g5 `27–33`, g6 `34–40`
  - L3: **restarts per track** — حسابات علمية `1–10`, ذكاء اصطناعى `1–3`, علوم حاسب `1–9`, نظم معلومات `1–6` (= 28 students)
  - L4: **restarts per track** — حسابات علمية `1–5`, ذكاء اصطناعى `1–3`, علوم حاسب `1–7`, نظم معلومات `1–4` (= 19 students)
- `students` totals: L1=50, L2=40, L3=28, L4=19 → **137**; `events` = **1561**.
- `events[].page` per level listed above (use as golden assertion).

### 4.5 Track / 4th-column rules
- L3/L4: the label at `x≈738` is the **track** (`حسابات علمية`, `ذكاء اصطناعى`, `علوم حاسب`, `نظم معلومات`) and the level is at `x≈757`.
- L1/L2: the label at `x≈757` contains junk like `رياضة` / `علوم`+`علمى` — **reference has `track: ""` for L1/L2 → assign track ONLY when level ≥ 3.**

### 4.6 Times
- Header rows give period start (row A) / end (row B): period1 = `09:00→09:45`, … period12 = `17:15→18:00` (shown as `05:15 / 06:00` 12h clock).
- **Use arithmetic, not clock parsing:** `start(k) = 09:00 + (k-1)*45min`, `end(k) = 09:00 + k*45min`. Validate against header text (mod 12h).
- Cell at `x0→x1` maps to `i0 = round((x0-50.21)/55.94)`, `i1 = round((x1-50.21)/55.94) - 1`; periods `k_right = 12 - i1` (earliest), `k_left = 12 - i0` (latest) → `start = start(k_right)`, `end = end(k_left)`.
- **Verified example:** page1 row3 cell `[610 → 721]` ⇒ `i0=10, i1=11` ⇒ `k_right=1, k_left=2` ⇒ `09:00 → 10:30` ✓ (matches reference).
- Output format: 24h **no leading zero** (`9:00`, `16:30`) — matches reference.

### 4.7 Arabic text fix — THE CRITICAL ORDER ⚠️
```python
def fix_line(line: str) -> str:
    s = line[::-1]                                   # 1) REVERSE FIRST (raw is visually mirrored)
    s = unicodedata.normalize("NFKC", s)             # 2) THEN expand presentation forms/ligatures
    s = re.sub(r"[0-9:.]+", lambda m: m.group(0)[::-1], s)  # 3) flip digit/time runs back
    s = s.replace("\u06cc", "\u064a").replace("\u06a9", "\u0643")  # 4) Persian yeh/kaf → Arabic
    return re.sub(r"\s+", " ", s).strip()

def cell_text(page, bbox) -> str:
    raw = page.crop(bbox).extract_text() or ""
    return " ".join(fix_line(line) for line in raw.split("\n"))  # keep line order (top→bottom)
```
- **Why reverse BEFORE NFKC:** the lam+alef-hamza ligature `ﻷ` (U+FEF7) must be reversed as a *single glyph*; NFKC-first then reverse yields `األولى` instead of `الأولى`. **Verified empirically.**
- **Apply `fix_line` per line**, not to the whole cell (otherwise lines swap).
- Digit runs MUST be re-flipped or `14` becomes `41` and `09:00` becomes `00:90`.

### 4.8 Extraction state machine (to implement in `tools/extract_schedule.py`)
```
for page in pdf:
  for table in page.find_tables():
    for row in table.rows:
      labels = [(x0, bbox) for cells with x0 >= 721]
      for (x0, bbox) in labels:
        txt = cell_text(page, bbox)
        if any(day in txt for day in DAYS):      current_day = day   # RESET level/group/track/section
        elif txt.isdigit() and x0 < 738:         current_section = int(txt)
        elif "المجموعة" in txt:                  current_group = parse_ordinal(txt)  # fallback: inherit
        elif "المستوى" in txt:                   current_level = parse_ordinal(txt)
        elif x0 >= 738 and current_level in (3,4): current_track = txt   # else ignore (L1/L2 junk)
      for cell in period cells (x0 < 721, not None):
        text = cell_text(page, cell)
        if text: emit {day, level, group, track, section, start, end, text, page}
```
- `parse_ordinal` on normalized text (`أ→ا`, `ى→ي`, strip `المجموعة`/`المستوى`): match in order `اول→1, ثان→2, ثالث→3, رابع→4, خامس→5, سادس→6, سابع→7`. If missing (e.g. clipped `المجموعة` alone) → **inherit previous value**.
- Output schema (must match reference exactly):
  `{"days":[6 names], "events":[{day,level,group,section,track,start,end,text,page}], "students":[{level,group,track,section}], "pages":{"1":"السبت",…}}`
  - `group`: `null` for L3/L4 (reference uses `null`, not `""`), `""` track for L1/L2.
  - `students` = distinct (level, group|track, section) — decide from events; golden test tells whether empty sections must be included.
- Also write `data/meta.json`: `generated_at`, `pdf_sha256`, `events_count`, `students_count`.

### 4.9 pdfplumber API gotchas discovered (saves time)
- `Table.rows` → list of **`Row` objects**: `.bbox` and `.cells` (NOT subscriptable).
- `Table.columns` → list of **`Column` objects**: `.bbox`, `.cells` (NO `.x0/.x1`).
- `row.cells[i]` = `(x0, top, x1, bottom)` or `None`.
- **`page.search('المستوى')` returns NOTHING** — page text is visually mirrored, so Arabic literals never match. Use `page.crop(bbox).extract_text()` per cell instead.
- `extract_words()` on this PDF returns **garbled per-glyph positions** (Arabic letters 1pt apart) — unreliable; crops work.
- `extract_tables()` gives text but loses merge/span info → **use `find_tables()` + `row.cells` bboxes**.

---

### 4.10 SCHEMA FACTS proven in session 2 (still binding — used by import + tests) ✅
- **Unique/diff key = `(day, level, group, track, section, start)`** — `track` is MANDATORY: without it the reference has **129 false duplicates** (L3/L4 section numbers restart at 1 in every track). With `track`: 0 duplicates. (Supersedes the plan/spec's original 5-field key — plan T3/T4 updated.)
- **Intentional asymmetry in the reference:** `events[].group = null` for L3/L4, but `students[].group = ""` for L3/L4. Preserve exactly (a golden test compares byte-level data).
- `students` ↔ event-sections are **1:1 (137 = 137)** — every section has ≥1 event; `students` can be validated as "every event's section exists in students".
- `pages` keys are strings `"1".."33"`, consecutive; `event.day == pages[str(event.page)]`.
- Time format: 24h **no leading zero** (`9:00`, `16:30`); grid = 45-min slots from 09:00 to 18:00.
- Event counts per (level, day) available in reference (L1 total 50 sections / L2 40 / L3 28 / L4 19 = 137; 1561 events).



## 5. FORMER OPEN ISSUES — ALL RESOLVED ✅ (session 2)

1. ✅ **RESOLVED — level label truncated.** Page 8 row16 DOES contain the L4 label: `الرابع لمستوى` (the PDF renders `لمستوى`, so match substring **`مستوى`**, not `المستوى`). Page 9's cell = fragment `ال` → ignore it + forward-fill level from page 8 (works; ground truth L4 pages 8,9,14,15,…). Fragments like `ال`/`المس` never satisfy the `مستوى` matcher → automatically ignored.
2. ✅ **RESOLVED — group off-by-one was a false alarm.** Full page-1 row dump: L1 group labels sit exactly on sections 1/8/15/22/29/37/44 and L2 on 1/7/13/20/27 — **identical to the reference** (the earlier confusion mixed row-index 59 with section number 7). Real quirk found instead: **P1 r79 label clipped to bare `المجموعة`** (ordinal not drawn) → rule: a lone `المجموعة` that starts a new group = **previous group + 1**; page 2 row0 re-states the full `المجموعة الخامسة` at section 30 (labels may reappear per page — harmless with forward-fill).
3. ✅ **INFO — Saturday page 1 contains L1+L2** (rows 3–52 = L1 sections 1–50, rows 53+ = L2 from section 1) — mid-page level switches are normal. *(Moot for production since parsing was abandoned; PROMPT A already warns ChatGPT about merged labels/forward-fill.)*
4. ℹ️ **Moot but documented:** P2 r29 has an empty track cell exactly where L3 track restarts to section 1 (would have needed special handling: forward-fill wrongly keeps `ذكاء اصطناعى`; the real track is `حسابات علمية`). Recorded in case PDF parsing is ever revived.

---

## 6. REMAINING WORK — EXACT STEPS (revised session 2; the PLAN FILE is authoritative)

**➡️ Execute in this order (read `docs/superpowers/plans/2026-10-03-cs-benha-schedule-plan.md` — T1/T2/T3/T4/T9 were rewritten there):**

### Phase 1 — foundation (start here)
- **T0 (finish):** `git init -b main` + local identity `Ahmed El3ssal <ahmedel3ssal1@gmail.com>` — ⛔ **only after Ahmed's approval; NO commit/push without asking him the commit message** (his rule).
- **T1 (REVISED — no PDF parsing):** write `tools/import_schedule.py`: `load_payload` → `validate` (rules = plan T1 + §4.10 facts: unique key **with `track`**, `group null/""` asymmetry, 45-min grid, day/page consistency, section∈students) → mechanical `auto_fix` only (spaces, `ی/ک`, leading zeros) → CLI writes `data/schedule.json` + `data/meta.json` {`generated_at`,`payload_sha256`,`events_count`,`students_count`,`source`}. **First import source = `tests/fixtures/reference-data.json`** (= scheadel `const DATA`). Future payloads live in `data/inbox/schedule-YYYY-MM-DD.json`.
  - Gate: 1561 events / 137 students / output **100% identical** to the reference.
- **T2 (quality gate — blocks everything):** `tests/test_schedule.py` (100% golden match + schema/consistency rules) + `tests/test_import.py` (validator units: bad track/time/dup-key/missing student, `09:00→9:00`, `ی→ي`, extra keys reported but not written). `python -m pytest -q` green 100%. ⛔ Any failure → stop & show Ahmed the report.
  - *(Old ≥95% text-match and `textnorm` tests are CANCELLED — there is no extraction anymore.)*
- **T3:** `tools/apply_overrides.py` (+ `data/overrides.json` empty) — schema = spec §2.3 **but `key` now includes `track`** + unit tests (update/delete/add/unknown-key = hard error).
- **T4:** `tools/diff_schedule.py` → `diff-report.md` (`added/removed/changed` keyed on **`day+level+group+track+section+start`**) + `tests/test_diff.py`.
- **T5:** `index.html` + `css/style.css` — design tokens from spec §3.1 (`--bg:#FAFAF8 --surface:#fff --ink:#1A1A1A --muted:#6B7280 --line:#E5E7EB --primary:#2563EB --primary-soft:#EFF6FF`, radius 18/12, subtle shadow), `<html lang="ar" dir="rtl">`, `<meta name="theme-color" content="#FAFAF8">`, header + 3 selectors (pills on desktop / selects on mobile) + "مواعيد النهارده" card + week grid + "عرض الأسبوع كاملًا" toggle + footer (source + `meta.json` date + "تحديث الجدول" button) + export/print/share buttons + loading/error/empty states. Fonts: **self-hosted subset** in `fonts/` (Cairo or IBM Plex Sans Arabic, Arabic+digits only). Verify with `python -m http.server 8000` + `agent-browser`.
- **T6:** `js/data.js` (fetch + validate `data/schedule.json`) + `js/app.js` (3 dependent selects, `localStorage`, URL params `?level=&cat=&section=`, render today+week sorted by start, `escapeHtml` everywhere, `aria-live="polite"` on results). Gate: pick L1/group1/section1 → shows `القضايا المجتمعية … 9:00 - 10:30`; reload keeps selection; shared URL restores state.
- **T7:** `css/print.css` (`@media print`: hide header/footer/buttons, full week on one page, show level/section header, `print-color-adjust: exact`). Gate via `agent-browser eval`.
- **T8:** `.github/workflows/ci.yml` (on push: `pip install -r tools/requirements.txt && pytest -q`) — runs after T10 creates the repo. *(Note: `tools/requirements.txt` still lists pdfplumber/pypdf from the abandoned approach — optional cleanup: slim to pytest only; ask Ahmed.)*

### Phase 2 — update pipeline (needs Ahmed's inputs)
- **T9 (REVISED):** `.github/workflows/update.yml` — trigger on **`data/**`** (NOT `pdf/**`): install → pytest (fail stops deploy) → apply Sheet overrides (after T11) → `diff_schedule.py` vs previous version → `diff-report.md` artifact → deploy Pages. **No extraction in CI** — `schedule.json` arrives already-validated via PROMPT B + agent commit.
- **T10:** publish — ⛔ **ask Ahmed first**: `gh repo create cs-benha-schedule --public --source . --push` → `gh api repos/{owner}/cs-benha-schedule/pages -X POST -f "source[branch]=main" -f "source[path]=/"` → verify `https://el3ssal.github.io/cs-benha-schedule/` (⚠️ **public repo required for free Pages** — confirm with Ahmed).
- **T11:** Google Sheet (`mirror` + `overrides` tabs) + service account + GitHub Secrets `GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_ID` + `tools/sheet_sync.py` (dep `gspread` → **ask permission before installing**). Ahmed must share the sheet with the service account email as **Editor**.
- **T12:** on-site upload form → Google Apps Script web app (SHA-256 passcode, PDF type/size ≤5MB, rate-limit, **Git Data API** for binary, PAT in Script Properties only) → commit triggers Action. Ahmed must create/deploy the Apps Script + supply the PAT.

### Phase 3 — polish
- **T13:** `manifest.json` + root `sw.js` (**cache-first shell, NETWORK-FIRST `data/schedule.json` with cache fallback, bump `CACHE_VERSION` every deploy** — else students see stale schedules forever) + icons 192/512.
- **T14:** accessibility/motion (`prefers-reduced-motion`, focus rings, Lighthouse ≥90).
- **T15:** `README.md` (how to update: **new PDF → PROMPT A on ChatGPT → paste payload + PROMPT B to the agent**; Sheet; upload form).

**Dependency order:** `T0→T1→T2` then `T5→T6→T7` then `T8,T10` then `T9→T11→T12` then `T13→T14→T15`. **T2 is the quality gate.**

---

## 7. RULES FOR THE CONTINUING SESSION (from Ahmed's global AGENTS.md)

- Reply in **Arabic** (Ahmed writes Arabic); keep technical terms in English.
- **Always ask before modifying files:** *"أكتب خطة خطوة بخطوة الأول، أم أعدّل الملفات فوراً؟"* — (this session: he chose **plan first**; the plan already exists → proceed with it, but confirm before each new phase).
- **Never commit/push without asking** for the exact commit message.
- **Never install dependencies without permission** (pdfplumber/pypdf already approved; `gspread` NOT yet).
- Repos default **private** → but Pages needs public ⇒ **explicitly confirm with Ahmed** before `--public`.
- Terminal publishing flow: `git init -b main` → `git add .` → `git commit` → `gh repo create <name> --public --source . --push`.
- End every reply with: *"هل هذه اخر المحادثة الحالية وتود تطبيق التعديلات ام لا"*.
- Memories/commands go to `C:\Users\ahmed\.config\opencode\.memories\` (session changelog, command history, rollback refs).

---

## 8. Useful commands already validated

```powershell
# explore PDF (works)
python -c "import pdfplumber,sys; sys.stdout.reconfigure(encoding='utf-8'); p=pdfplumber.open(r'C:\Users\ahmed\Desktop\coll\cs-benha-schedule\pdf\جدول-العام.pdf'); tb=p.pages[0].find_tables()[0]; print(len(tb.rows), tb.rows[3].cells)"
# reference fixture already generated:
# tests/fixtures/reference-data.json  (1561 events / 137 students / 33 pages)
```
Failed/wrong approaches to avoid: `row[1]` subscripting on `Row`; `col.x0` on `Column`; `page.search('ال…')` on mirrored text; `extract_tables()` for span detection; reversing AFTER NFKC.
