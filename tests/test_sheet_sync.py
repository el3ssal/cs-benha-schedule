"""Unit tests for tools/sheet_sync.py (pure row parser only, no network)."""

import pytest

from tools.sheet_sync import HEADERS, SheetError, parse_override_rows


def make_row(**parts: str) -> list:
    record = {name: "" for name in HEADERS}
    record.update(parts)
    return [record[name] for name in HEADERS]


def base_key() -> dict:
    return {
        "op": "update",
        "day": "السبت",
        "level": "1",
        "group": "1",
        "track": "",
        "section": "1",
        "start": "9:00",
    }


def test_update_row_parsed() -> None:
    rows = [make_row(**{**base_key(), "set_text": "نص جديد"})]
    overrides = parse_override_rows(rows)
    assert overrides == [
        {
            "op": "update",
            "key": {
                "day": "السبت",
                "level": "1",
                "group": "1",
                "track": "",
                "section": "1",
                "start": "9:00",
            },
            "set": {"text": "نص جديد"},
        }
    ]


def test_delete_row_parsed() -> None:
    rows = [make_row(**{**base_key(), "op": "delete"})]
    overrides = parse_override_rows(rows)
    assert overrides[0]["op"] == "delete"
    assert "set" not in overrides[0]


def test_add_row_parsed() -> None:
    rows = [
        make_row(
            **{
                **base_key(),
                "op": "add",
                "start": "10:30",
                "text": "مادة جديدة",
                "end": "12:00",
                "page": "1",
            }
        )
    ]
    overrides = parse_override_rows(rows)
    assert overrides[0]["event"]["text"] == "مادة جديدة"
    assert overrides[0]["event"]["page"] == 1


def test_l3_empty_group_becomes_none() -> None:
    rows = [
        make_row(
            op="delete",
            day="السبت",
            level="3",
            group="",
            track="علوم حاسب",
            section="1",
            start="9:00",
        )
    ]
    overrides = parse_override_rows(rows)
    assert overrides[0]["key"]["group"] is None


def test_blank_rows_skipped() -> None:
    assert parse_override_rows([[""] * len(HEADERS), []]) == []


def test_bad_op_is_error() -> None:
    rows = [make_row(**{**base_key(), "op": "rename"})]
    with pytest.raises(SheetError):
        parse_override_rows(rows)


def test_update_without_set_is_error() -> None:
    with pytest.raises(SheetError):
        parse_override_rows([make_row(**base_key())])


def test_add_without_event_fields_is_error() -> None:
    rows = [make_row(**{**base_key(), "op": "add"})]
    with pytest.raises(SheetError):
        parse_override_rows(rows)
