"""Apply manual overrides on top of an imported schedule.

An overrides file holds {"overrides": [...]} where each entry follows spec
section 2.3 (key now includes track -- without it L3/L4 sections that restart
at 1 in every track are ambiguous):

  {"op": "update", "key": {...}, "set": {"text": ...}, "note": ..., ...}
  {"op": "delete", "key": {...}, ...}
  {"op": "add", "key": {...}, "event": {...full event...}, ...}

Rules: update/delete on an unknown key is a HARD error (fail loudly, never
silently skip). add with an already-existing key is a hard error. The result
is re-validated with import_schedule.validate before writing.

Only stdlib is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.import_schedule import EVENT_KEYS, canonical_schedule, validate  # noqa: E402

OVERRIDE_OPS = ("update", "delete", "add")
KEY_FIELDS = ("day", "level", "group", "track", "section", "start")
SETTABLE_FIELDS = ("text", "start", "end")


class OverrideError(ValueError):
    """Raised when an override cannot be applied (unknown key, bad schema)."""


def event_key(event: dict) -> tuple:
    return tuple(event[field] for field in KEY_FIELDS)


def normalize_key(raw_key: dict, label: str) -> tuple:
    if not isinstance(raw_key, dict):
        raise OverrideError(f"{label}: key must be an object")
    missing = [field for field in KEY_FIELDS if field not in raw_key]
    if missing:
        raise OverrideError(f"{label}: key missing fields {missing}")
    return tuple(raw_key[field] for field in KEY_FIELDS)


def apply_overrides(schedule: dict, overrides: list[dict]) -> dict:
    """Apply overrides in order; return a NEW schedule dict (validated)."""
    events = [dict(event) for event in schedule["events"]]
    index = {event_key(event): pos for pos, event in enumerate(events)}

    for pos, override in enumerate(overrides):
        label = f"overrides[{pos}]"
        if not isinstance(override, dict):
            raise OverrideError(f"{label}: must be an object")
        op = override.get("op")
        if op not in OVERRIDE_OPS:
            raise OverrideError(f"{label}: bad op {op!r} (want one of {OVERRIDE_OPS})")
        key = normalize_key(override.get("key"), label)

        if op == "update":
            if key not in index:
                raise OverrideError(f"{label}: update on unknown key {key!r}")
            changes = override.get("set")
            if not isinstance(changes, dict) or not changes:
                raise OverrideError(f"{label}: update needs a non-empty 'set' object")
            unknown = [field for field in changes if field not in SETTABLE_FIELDS]
            if unknown:
                raise OverrideError(f"{label}: cannot set fields {unknown}")
            target = events[index[key]]
            target.update(changes)
            new_key = event_key(target)
            if new_key != key and new_key in index:
                raise OverrideError(f"{label}: update collides with {new_key!r}")
            del index[key]
            index[new_key] = events.index(target)

        elif op == "delete":
            if key not in index:
                raise OverrideError(f"{label}: delete on unknown key {key!r}")
            removed = events.pop(index[key])
            assert event_key(removed) == key
            index = {event_key(event): i for i, event in enumerate(events)}

        elif op == "add":
            if key in index:
                raise OverrideError(f"{label}: add collides with existing {key!r}")
            new_event = override.get("event")
            if not isinstance(new_event, dict):
                raise OverrideError(f"{label}: add needs a full 'event' object")
            missing = [field for field in EVENT_KEYS if field not in new_event]
            if missing:
                raise OverrideError(f"{label}: event missing keys {missing}")
            if event_key(new_event) != key:
                raise OverrideError(f"{label}: event does not match key {key!r}")
            events.append({field: new_event[field] for field in EVENT_KEYS})
            index[key] = len(events) - 1

    result = dict(schedule)
    result["events"] = events
    errors, _warnings = validate(
        {
            "days": result["days"],
            "events": result["events"],
            "students": result["students"],
            "pages": result["pages"],
        }
    )
    if errors:
        raise OverrideError(f"result failed validation: {errors[0]}")
    return result


def load_overrides(path: str | Path) -> list[dict]:
    raw_path = Path(path)
    if not raw_path.exists():
        return []
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("overrides", [])
    if not isinstance(data, list):
        raise OverrideError("overrides file must hold a list (or {'overrides': [...]})")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply overrides JSON on top of data/schedule.json"
    )
    parser.add_argument("schedule", help="input schedule.json")
    parser.add_argument(
        "--overrides", default="data/overrides.json", help="overrides file"
    )
    parser.add_argument("--out", default="data/schedule.json", help="output path")
    args = parser.parse_args(argv)

    try:
        schedule = json.loads(Path(args.schedule).read_text(encoding="utf-8"))
        overrides = load_overrides(args.overrides)
        result = apply_overrides(schedule, overrides)
    except (OverrideError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(canonical_schedule(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OK: applied {len(overrides)} override(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
