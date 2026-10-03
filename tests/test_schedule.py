"""Golden + consistency tests for data/schedule.json (quality gate).

test_matches_reference: schedule.json must be 100% identical (parsed) to the
reference fixture it was imported from -- any difference is an import bug.
test_schema_consistency: the same validator rules re-run on any future import.
test_meta_consistency: data/meta.json exists and its counts match schedule.json.
"""

import json
from pathlib import Path

from tools.import_schedule import EXPECTED_DAYS, validate

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = ROOT / "data" / "schedule.json"
META_PATH = ROOT / "data" / "meta.json"
REFERENCE_PATH = ROOT / "tests" / "fixtures" / "reference-data.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_matches_reference() -> None:
    schedule = load_json(SCHEDULE_PATH)
    reference = load_json(REFERENCE_PATH)
    assert len(schedule["events"]) == 1561
    assert len(schedule["students"]) == 137
    assert schedule == reference


def test_schema_consistency() -> None:
    schedule = load_json(SCHEDULE_PATH)
    errors, _warnings = validate(schedule)
    assert errors == []
    assert schedule["days"] == EXPECTED_DAYS
    seen_keys = set()
    for event in schedule["events"]:
        key = (
            event["day"],
            event["level"],
            event["group"],
            event["track"],
            event["section"],
            event["start"],
        )
        assert key not in seen_keys
        seen_keys.add(key)
        assert schedule["pages"][str(event["page"])] == event["day"]


def test_meta_consistency() -> None:
    schedule = load_json(SCHEDULE_PATH)
    meta = load_json(META_PATH)
    for key in (
        "generated_at",
        "payload_sha256",
        "events_count",
        "students_count",
        "source",
    ):
        assert key in meta, f"meta.json missing key {key!r}"
    assert meta["events_count"] == len(schedule["events"])
    assert meta["students_count"] == len(schedule["students"])
