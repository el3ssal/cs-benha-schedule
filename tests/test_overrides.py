"""Unit tests for tools/apply_overrides.py."""

import copy

import pytest

from tools.apply_overrides import OverrideError, apply_overrides, load_overrides


def make_schedule() -> dict:
    return {
        "days": ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"],
        "events": [
            {
                "day": "السبت",
                "level": "1",
                "group": "1",
                "section": "1",
                "track": "",
                "start": "9:00",
                "end": "10:30",
                "text": "نص قديم",
                "page": 1,
            }
        ],
        "students": [{"level": "1", "group": "1", "track": "", "section": "1"}],
        "pages": {"1": "السبت"},
    }


def make_key(**parts: object) -> dict:
    key = {
        "day": "السبت",
        "level": "1",
        "group": "1",
        "track": "",
        "section": "1",
        "start": "9:00",
    }
    key.update(parts)
    return key


def test_update_changes_cell() -> None:
    result = apply_overrides(
        make_schedule(),
        [{"op": "update", "key": make_key(), "set": {"text": "نص جديد"}}],
    )
    assert result["events"][0]["text"] == "نص جديد"
    assert len(result["events"]) == 1


def test_delete_removes_event() -> None:
    result = apply_overrides(make_schedule(), [{"op": "delete", "key": make_key()}])
    assert result["events"] == []


def test_add_inserts_event() -> None:
    schedule = make_schedule()
    new_event = dict(schedule["events"][0])
    new_event["start"] = "10:30"
    new_event["end"] = "12:00"
    new_event["text"] = "مادة مضافة"
    result = apply_overrides(
        schedule,
        [{"op": "add", "key": make_key(start="10:30"), "event": new_event}],
    )
    assert len(result["events"]) == 2
    assert result["events"][1]["text"] == "مادة مضافة"


def test_unknown_key_is_hard_error() -> None:
    with pytest.raises(OverrideError):
        apply_overrides(
            make_schedule(),
            [{"op": "update", "key": make_key(section="99"), "set": {"text": "x"}}],
        )
    with pytest.raises(OverrideError):
        apply_overrides(
            make_schedule(), [{"op": "delete", "key": make_key(section="99")}]
        )


def test_add_colliding_key_is_error() -> None:
    schedule = make_schedule()
    with pytest.raises(OverrideError):
        apply_overrides(
            schedule,
            [{"op": "add", "key": make_key(), "event": dict(schedule["events"][0])}],
        )


def test_bad_op_is_error() -> None:
    with pytest.raises(OverrideError):
        apply_overrides(make_schedule(), [{"op": "rename", "key": make_key()}])


def test_load_overrides_missing_file_is_empty(tmp_path) -> None:
    assert load_overrides(tmp_path / "nope.json") == []


def test_apply_does_not_mutate_input() -> None:
    schedule = make_schedule()
    snapshot = copy.deepcopy(schedule)
    apply_overrides(schedule, [{"op": "update", "key": make_key(), "set": {"text": "نص جديد"}}])
    assert schedule == snapshot
