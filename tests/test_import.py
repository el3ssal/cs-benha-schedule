"""Unit tests for tools/import_schedule.py (validator + auto-fix)."""

import copy
import json

from tools.import_schedule import (
    EXPECTED_DAYS,
    apply_auto_fixes,
    canonical_schedule,
    validate,
)


def make_payload() -> dict:
    day = EXPECTED_DAYS[0]
    return {
        "days": list(EXPECTED_DAYS),
        "events": [
            {
                "day": day,
                "level": "1",
                "group": "1",
                "section": "1",
                "track": "",
                "start": "9:00",
                "end": "10:30",
                "text": "القضايا المجتمعية د/ مصطفى عبدالله اونلاين",
                "page": 1,
            }
        ],
        "students": [{"level": "1", "group": "1", "track": "", "section": "1"}],
        "pages": {"1": day},
    }


def make_l3_event(day: str, track: str, section: str, start: str = "9:00") -> dict:
    return {
        "day": day,
        "level": "3",
        "group": None,
        "section": section,
        "track": track,
        "start": start,
        "end": "10:30",
        "text": "مادة تجريبية",
        "page": 1,
    }


def make_l3_student(track: str, section: str) -> dict:
    return {"level": "3", "group": "", "track": track, "section": section}


def assert_valid(payload: dict) -> None:
    errors, _warnings = validate(payload)
    assert errors == [], f"expected valid, got: {errors}"


def test_valid_payload_passes() -> None:
    assert_valid(make_payload())


def test_bad_track_is_error() -> None:
    payload = make_payload()
    payload["events"][0]["track"] = "علوم حاسب"  # L1 must have empty track
    errors, _warnings = validate(payload)
    assert any("track" in err for err in errors)


def test_bad_l3_track_is_error() -> None:
    payload = make_payload()
    day = EXPECTED_DAYS[0]
    payload["events"] = [make_l3_event(day, "تخصص وهمي", "1")]
    payload["students"] = [make_l3_student("تخصص وهمي", "1")]
    errors, _warnings = validate(payload)
    assert any("track" in err for err in errors)


def test_time_off_grid_is_error() -> None:
    payload = make_payload()
    payload["events"][0]["start"] = "9:10"
    errors, _warnings = validate(payload)
    assert any("grid" in err for err in errors)


def test_end_before_start_is_error() -> None:
    payload = make_payload()
    payload["events"][0]["start"] = "11:15"
    payload["events"][0]["end"] = "10:30"
    errors, _warnings = validate(payload)
    assert any("must be after start" in err for err in errors)


def test_duplicate_full_key_is_error() -> None:
    payload = make_payload()
    payload["events"].append(copy.deepcopy(payload["events"][0]))
    errors, _warnings = validate(payload)
    assert any("duplicate key" in err for err in errors)


def test_same_section_different_track_is_ok() -> None:
    """track is part of the key: same section in two tracks must NOT collide."""
    payload = make_payload()
    day = EXPECTED_DAYS[0]
    payload["events"] = [
        make_l3_event(day, "علوم حاسب", "1"),
        make_l3_event(day, "نظم معلومات", "1"),
    ]
    payload["students"] = [
        make_l3_student("علوم حاسب", "1"),
        make_l3_student("نظم معلومات", "1"),
    ]
    assert_valid(payload)


def test_missing_student_section_is_error() -> None:
    payload = make_payload()
    payload["students"] = []
    errors, _warnings = validate(payload)
    assert any("missing in students" in err for err in errors)


def test_leading_zero_is_auto_fixed() -> None:
    payload = make_payload()
    payload["events"][0]["start"] = "09:00"
    fixed, fixes = apply_auto_fixes(payload)
    assert fixed["events"][0]["start"] == "9:00"
    assert fixes, "expected at least one fix to be reported"
    assert_valid(fixed)


def test_persian_chars_are_auto_fixed() -> None:
    payload = make_payload()
    payload["events"][0]["text"] = "القض\u06cc\u06a9ا"  # Persian yeh + kaf
    fixed, fixes = apply_auto_fixes(payload)
    assert fixed["events"][0]["text"] == "القضيكا"
    assert fixes
    assert_valid(fixed)


def test_missing_key_is_error() -> None:
    payload = make_payload()
    del payload["events"][0]["text"]
    errors, _warnings = validate(payload)
    assert any("missing keys" in err for err in errors)


def test_extra_top_level_keys_warn_but_do_not_fail() -> None:
    payload = make_payload()
    payload["issues"] = "page 9 illegible"
    payload["summary"] = {"events": 1}
    errors, warnings = validate(payload)
    assert errors == []
    assert any("issues" in warn for warn in warnings)
    schedule = canonical_schedule(payload)
    assert set(schedule) == {"days", "events", "students", "pages"}
    json.dumps(schedule, ensure_ascii=False)  # must stay serializable


def test_l3_group_asymmetry_is_enforced() -> None:
    payload = make_payload()
    day = EXPECTED_DAYS[0]
    payload["events"] = [make_l3_event(day, "علوم حاسب", "1")]
    payload["students"] = [make_l3_student("علوم حاسب", "1")]
    assert_valid(payload)
    bad_event = make_payload()
    bad_event["events"] = [make_l3_event(day, "علوم حاسب", "1")]
    bad_event["events"][0]["group"] = ""  # must be null, not ""
    bad_event["students"] = [make_l3_student("علوم حاسب", "1")]
    errors, _warnings = validate(bad_event)
    assert any("must be null" in err for err in errors)
    bad_student = make_payload()
    bad_student["events"] = [make_l3_event(day, "علوم حاسب", "1")]
    bad_student["students"] = [make_l3_student("علوم حاسب", "1")]
    bad_student["students"][0]["group"] = None  # must be "", not null
    errors, _warnings = validate(bad_student)
    assert any("must be ''" in err for err in errors)


def test_day_page_mismatch_is_error() -> None:
    payload = make_payload()
    payload["pages"] = {"1": EXPECTED_DAYS[1]}  # event says EXPECTED_DAYS[0]
    errors, _warnings = validate(payload)
    assert any("pages[1]" in err for err in errors)
