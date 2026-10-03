"""Import a ChatGPT-extracted timetable payload into data/schedule.json.

Pipeline: load_payload -> apply_auto_fixes -> validate -> write outputs.

Data source: scheadel ``const DATA`` (see tests/fixtures/reference-data.json).
Future updates arrive as ChatGPT payloads (docs/PROMPTS.md, PROMPT A/B) saved
under data/inbox/schedule-YYYY-MM-DD.json. No PDF parsing happens here.

The unique/diff key is (day, level, group, track, section, start) -- track is
MANDATORY (L3/L4 section numbers restart at 1 in every track).

Intentional asymmetry (preserved exactly):
  events[].group is None for L3/L4, while students[].group is "" for L3/L4.

Only stdlib is used (no new dependencies).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_DAYS = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]

ALLOWED_TRACKS = {"حسابات علمية", "ذكاء اصطناعى", "علوم حاسب", "نظم معلومات"}

ALLOWED_LEVELS = {"1", "2", "3", "4"}

TOP_KEYS = ("days", "events", "students", "pages")

EVENT_KEYS = ("day", "level", "group", "section", "track", "start", "end", "text", "page")

STUDENT_KEYS = ("level", "group", "track", "section")

# 45-minute slots from 09:00 to 18:00, no leading zero (matches the reference).
GRID = [
    "9:00", "9:45", "10:30", "11:15", "12:00", "12:45", "13:30",
    "14:15", "15:00", "15:45", "16:30", "17:15", "18:00",
]
GRID_SET = set(GRID)

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
LEADING_ZERO_RE = re.compile(r"^0(\d:\d{2})$")

PERSIAN_YEH = "\u06cc"
ARABIC_YEH = "\u064a"
PERSIAN_KAF = "\u06a9"
ARABIC_KAF = "\u0643"

# Arabic Presentation Forms blocks: text containing these was never shaped
# correctly (mirrored/clipped source) and must be rejected, not guessed.
PRESENTATION_RANGES = ((0xFB50, 0xFDFF), (0xFE70, 0xFEFF))

MAX_REPORT_LINES = 20


def minutes_of(value: str) -> int:
    """Convert 'H:MM' to minutes since midnight (string compare is WRONG here)."""
    match = TIME_RE.match(value)
    if match is None:
        raise ValueError(f"bad time format: {value!r}")
    return int(match.group(1)) * 60 + int(match.group(2))


def load_payload(path: str | Path) -> dict:
    """Load a JSON payload file (utf-8). Raises on missing file/bad JSON."""
    raw_path = Path(path)
    text = raw_path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("payload root must be a JSON object")
    return payload


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def fix_time_value(value: object) -> tuple[str, bool]:
    """Strip whitespace and remove a leading zero ('09:00' -> '9:00')."""
    if not isinstance(value, str):
        return value, False
    cleaned = value.strip()
    fixed = LEADING_ZERO_RE.sub(r"\1", cleaned)
    return fixed, fixed != value


def apply_auto_fixes(payload: dict) -> tuple[dict, list[str]]:
    """Apply MECHANICAL fixes only; return (fixed_payload, fixes).

    Allowed: whitespace collapse, Persian yeh/kaf -> Arabic, leading-zero
    removal in times. Anything semantic is left untouched for validate().
    """
    fixes: list[str] = []
    fixed: dict = dict(payload)

    events = payload.get("events")
    if isinstance(events, list):
        new_events = []
        for idx, event in enumerate(events):
            if not isinstance(event, dict):
                new_events.append(event)
                continue
            new_event = dict(event)
            text = new_event.get("text")
            if isinstance(text, str):
                new_text = collapse_spaces(
                    text.replace(PERSIAN_YEH, ARABIC_YEH).replace(PERSIAN_KAF, ARABIC_KAF)
                )
                if new_text != text:
                    fixes.append(f"events[{idx}].text: mechanical cleanup")
                    new_event["text"] = new_text
            for field in ("start", "end"):
                new_value, changed = fix_time_value(new_event.get(field))
                if changed:
                    fixes.append(f"events[{idx}].{field}: {event.get(field)!r} -> {new_value!r}")
                    new_event[field] = new_value
            for field in ("day", "level", "group", "section", "track"):
                old_value = new_event.get(field)
                if isinstance(old_value, str):
                    stripped = old_value.strip()
                    if stripped != old_value:
                        fixes.append(f"events[{idx}].{field}: whitespace stripped")
                        new_event[field] = stripped
            new_events.append(new_event)
        fixed["events"] = new_events

    students = payload.get("students")
    if isinstance(students, list):
        new_students = []
        for idx, student in enumerate(students):
            if not isinstance(student, dict):
                new_students.append(student)
                continue
            new_student = dict(student)
            for field in ("level", "group", "section", "track"):
                old_value = new_student.get(field)
                if isinstance(old_value, str):
                    stripped = old_value.strip()
                    if stripped != old_value:
                        fixes.append(f"students[{idx}].{field}: whitespace stripped")
                        new_student[field] = stripped
            new_students.append(new_student)
        fixed["students"] = new_students

    return fixed, fixes


def has_presentation_forms(value: str) -> bool:
    return any(
        any(low <= ord(char) <= high for low, high in PRESENTATION_RANGES)
        for char in value
    )


def validate(payload: dict) -> tuple[list[str], list[str]]:
    """Validate a (fixed) payload. Returns (errors, warnings).

    Extra top-level keys (e.g. ChatGPT 'issues'/'summary') are warnings only;
    they are reported but never written to schedule.json.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return ["payload root must be a JSON object"], warnings

    for key in TOP_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key!r}")
    for key in payload:
        if key not in TOP_KEYS:
            warnings.append(f"extra top-level key {key!r} reported (not written)")

    days = payload.get("days")
    if days is not None and days != EXPECTED_DAYS:
        errors.append(f"days must be exactly {EXPECTED_DAYS}")

    pages = payload.get("pages")
    page_count = 0
    if pages is not None:
        if not isinstance(pages, dict):
            errors.append("pages must be an object mapping page number -> day")
            pages = None
        else:
            try:
                numbers = sorted(int(key) for key in pages)
            except (TypeError, ValueError):
                errors.append("pages keys must be consecutive integers from '1'")
                numbers = []
            if numbers and numbers != list(range(1, len(numbers) + 1)):
                errors.append("pages keys must be consecutive integers from '1'")
            else:
                page_count = len(numbers)
            for key, day in pages.items():
                if day not in EXPECTED_DAYS:
                    errors.append(f"pages[{key!r}]: unknown day {day!r}")

    events = payload.get("events")
    if events is not None:
        if not isinstance(events, list):
            errors.append("events must be a list")
            events = None
        else:
            seen_keys: dict[tuple, int] = {}
            for idx, event in enumerate(events):
                label = f"events[{idx}]"
                if not isinstance(event, dict):
                    errors.append(f"{label}: must be an object")
                    continue
                missing = [key for key in EVENT_KEYS if key not in event]
                extra = [key for key in event if key not in EVENT_KEYS]
                if missing:
                    errors.append(f"{label}: missing keys {missing}")
                    continue
                if extra:
                    errors.append(f"{label}: extra keys {extra}")
                    continue
                level = event["level"]
                group = event["group"]
                track = event["track"]
                if level not in ALLOWED_LEVELS:
                    errors.append(f"{label}: bad level {level!r}")
                    continue
                if level in ("1", "2"):
                    if track != "":
                        errors.append(f"{label}: L1/L2 track must be empty, got {track!r}")
                    if not isinstance(group, str) or not group.isdigit():
                        errors.append(f"{label}: L1/L2 group must be a digit string")
                else:
                    if track not in ALLOWED_TRACKS:
                        errors.append(f"{label}: bad L3/L4 track {track!r}")
                    if group is not None:
                        errors.append(f"{label}: L3/L4 group must be null (got {group!r})")
                section = event["section"]
                if not isinstance(section, str) or not section.isdigit():
                    errors.append(f"{label}: section must be a digit string")
                day = event["day"]
                if day not in EXPECTED_DAYS:
                    errors.append(f"{label}: unknown day {day!r}")
                for field in ("start", "end"):
                    value = event[field]
                    if not isinstance(value, str) or TIME_RE.match(value) is None:
                        errors.append(f"{label}: bad time {field}={value!r}")
                    elif LEADING_ZERO_RE.match(value):
                        errors.append(f"{label}: time {field}={value!r} has a leading zero")
                    elif value not in GRID_SET:
                        errors.append(f"{label}: time {field}={value!r} not on the 45-min grid")
                start = event["start"]
                end = event["end"]
                if (
                    isinstance(start, str)
                    and isinstance(end, str)
                    and TIME_RE.match(start)
                    and TIME_RE.match(end)
                    and minutes_of(end) <= minutes_of(start)
                ):
                    errors.append(f"{label}: end {end!r} must be after start {start!r}")
                text = event["text"]
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"{label}: text must be a non-empty string")
                elif PERSIAN_YEH in text or PERSIAN_KAF in text:
                    errors.append(f"{label}: text still contains Persian yeh/kaf")
                elif has_presentation_forms(text):
                    errors.append(f"{label}: text contains presentation forms (mirrored?)")
                page = event["page"]
                if not isinstance(page, int) or isinstance(page, bool):
                    errors.append(f"{label}: page must be an integer")
                elif pages is not None and not 1 <= page <= page_count:
                    errors.append(f"{label}: page {page} out of range 1..{page_count}")
                elif (
                    pages is not None
                    and isinstance(page, int)
                    and str(page) in pages
                    and day in EXPECTED_DAYS
                    and pages[str(page)] != day
                ):
                    errors.append(
                        f"{label}: day {day!r} != pages[{page}] ({pages[str(page)]!r})"
                    )
                key = (day, level, group, track, section, start)
                if key in seen_keys:
                    errors.append(
                        f"{label}: duplicate key {key!r} (first at events[{seen_keys[key]}])"
                    )
                else:
                    seen_keys[key] = idx

    students = payload.get("students")
    student_set: set[tuple] = set()
    if students is not None:
        if not isinstance(students, list):
            errors.append("students must be a list")
            students = None
        else:
            for idx, student in enumerate(students):
                label = f"students[{idx}]"
                if not isinstance(student, dict):
                    errors.append(f"{label}: must be an object")
                    continue
                missing = [key for key in STUDENT_KEYS if key not in student]
                extra = [key for key in student if key not in STUDENT_KEYS]
                if missing:
                    errors.append(f"{label}: missing keys {missing}")
                    continue
                if extra:
                    errors.append(f"{label}: extra keys {extra}")
                    continue
                level = student["level"]
                group = student["group"]
                track = student["track"]
                section = student["section"]
                if level not in ALLOWED_LEVELS:
                    errors.append(f"{label}: bad level {level!r}")
                    continue
                if level in ("1", "2"):
                    if track != "":
                        errors.append(f"{label}: L1/L2 track must be empty")
                    if not isinstance(group, str) or not group.isdigit():
                        errors.append(f"{label}: L1/L2 group must be a digit string")
                else:
                    if track not in ALLOWED_TRACKS:
                        errors.append(f"{label}: bad L3/L4 track {track!r}")
                    if group != "":
                        errors.append(f"{label}: L3/L4 group must be '' (got {group!r})")
                if not isinstance(section, str) or not section.isdigit():
                    errors.append(f"{label}: section must be a digit string")
                student_set.add((level, group, track, section))

    if events and students is not None and isinstance(students, list):
        for idx, event in enumerate(events):
            if not isinstance(event, dict):
                continue
            if any(key not in event for key in ("level", "group", "track", "section")):
                continue
            group = event["group"]
            section_key = (
                event["level"],
                "" if group is None else group,
                event["track"],
                event["section"],
            )
            if section_key not in student_set:
                errors.append(f"events[{idx}]: section {section_key!r} missing in students")

    return errors, warnings


def canonical_schedule(payload: dict) -> dict:
    """Return the canonical schedule object (only the 4 official keys)."""
    return {
        "days": list(payload["days"]),
        "events": [
            {key: event[key] for key in EVENT_KEYS} for event in payload["events"]
        ],
        "students": [
            {key: student[key] for key in STUDENT_KEYS}
            for student in payload["students"]
        ],
        "pages": dict(payload["pages"]),
    }


def write_json(path: str | Path, data: dict) -> None:
    raw_path = Path(path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_meta(payload_sha256: str, schedule: dict, source: str) -> dict:
    generated_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    return {
        "generated_at": generated_at,
        "payload_sha256": payload_sha256,
        "events_count": len(schedule["events"]),
        "students_count": len(schedule["students"]),
        "source": source,
    }


def print_report(title: str, lines: list[str]) -> None:
    print(f"{title} ({len(lines)}):")
    for line in lines[:MAX_REPORT_LINES]:
        print(f"  - {line}")
    if len(lines) > MAX_REPORT_LINES:
        print(f"  ... and {len(lines) - MAX_REPORT_LINES} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a timetable payload and write data/schedule.json + data/meta.json"
    )
    parser.add_argument("payload", help="input JSON payload (ChatGPT output or fixture)")
    parser.add_argument("--out", default="data/schedule.json", help="schedule output path")
    parser.add_argument("--meta", default="data/meta.json", help="meta output path")
    parser.add_argument(
        "--source",
        default="chatgpt-import",
        help="origin label recorded in meta.json",
    )
    args = parser.parse_args(argv)

    try:
        raw_text = Path(args.payload).read_text(encoding="utf-8")
        payload = json.loads(raw_text)
    except FileNotFoundError:
        print(f"ERROR: payload file not found: {args.payload}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: payload is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("ERROR: payload root must be a JSON object", file=sys.stderr)
        return 1

    payload_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    fixed, fixes = apply_auto_fixes(payload)
    errors, warnings = validate(fixed)

    if errors:
        print(f"FAILED with {len(errors)} error(s):", file=sys.stderr)
        for line in errors[:MAX_REPORT_LINES]:
            print(f"  - {line}", file=sys.stderr)
        if len(errors) > MAX_REPORT_LINES:
            print(
                f"  ... and {len(errors) - MAX_REPORT_LINES} more", file=sys.stderr
            )
        return 1

    schedule = canonical_schedule(fixed)
    write_json(args.out, schedule)
    write_json(args.meta, build_meta(payload_sha256, schedule, args.source))

    print(
        f"OK: {len(schedule['events'])} events, "
        f"{len(schedule['students'])} students -> {args.out} (+ {args.meta})"
    )
    print_report("fixes", fixes)
    print_report("warnings", warnings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
