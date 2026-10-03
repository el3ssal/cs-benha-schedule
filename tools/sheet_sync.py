"""Sync with the Google Sheet (T11): mirror tab + overrides tab.

Sheet layout (tab `overrides`, first row = header):
  op | day | level | group | track | section | start |
  set_text | set_start | set_end | text | end | page |
  note | author | date

- update: key columns (day..start) + any of set_text/set_start/set_end.
- delete: key columns only.
- add: key columns + text + end + page (a full new event).
- Empty group cell with level 3/4 means null (matches events schema).

Tab `mirror` is display-only: rewritten from data/schedule.json after import.

Auth: a service account shared on the sheet as Editor. Credentials come from
env GOOGLE_SERVICE_ACCOUNT_JSON (JSON content or a file path) or
--service-account (file path). Needs `gspread` (ask before installing).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OVERRIDES_TAB = "overrides"
MIRROR_TAB = "mirror"

HEADERS = [
    "op", "day", "level", "group", "track", "section", "start",
    "set_text", "set_start", "set_end", "text", "end", "page",
    "note", "author", "date",
]

KEY_COLUMNS = ("day", "level", "group", "track", "section", "start")
UPDATEABLE = ("set_text", "set_start", "set_end")


class SheetError(ValueError):
    """Raised for bad sheet rows or missing credentials."""


def blank_to_none(value: str) -> str | None:
    text = (value or "").strip()
    return text if text != "" else None


def parse_override_rows(rows: list[list]) -> list[dict]:
    """Parse raw sheet rows (WITHOUT header) into override dicts (pure)."""
    overrides = []
    for line_no, row in enumerate(rows, start=2):
        cells = [(cell or "").strip() for cell in list(row) + [""] * len(HEADERS)]
        record = dict(zip(HEADERS, cells))
        if all(cell == "" for cell in cells):
            continue  # blank row
        op = record["op"]
        if op not in ("update", "delete", "add"):
            raise SheetError(f"row {line_no}: bad op {op!r}")
        key = {field: record[field] for field in KEY_COLUMNS}
        if key["level"] in ("3", "4") and key["group"] == "":
            key["group"] = None
        override: dict = {"op": op, "key": key}
        for extra in ("note", "author", "date"):
            if record[extra]:
                override[extra] = record[extra]
        if op == "update":
            changes = {}
            if record["set_text"]:
                changes["text"] = record["set_text"]
            if record["set_start"]:
                changes["start"] = record["set_start"]
            if record["set_end"]:
                changes["end"] = record["set_end"]
            if not changes:
                raise SheetError(f"row {line_no}: update needs a set_* value")
            override["set"] = changes
        elif op == "add":
            if not record["text"] or not record["end"] or not record["page"]:
                raise SheetError(f"row {line_no}: add needs text+end+page")
            try:
                page = int(record["page"])
            except ValueError:
                raise SheetError(f"row {line_no}: bad page {record['page']!r}")
            override["event"] = {
                "day": key["day"],
                "level": key["level"],
                "group": key["group"],
                "section": key["section"],
                "track": key["track"],
                "start": key["start"],
                "end": record["end"],
                "text": record["text"],
                "page": page,
            }
        overrides.append(override)
    return overrides


def open_sheet(sheet_id: str, service_account: str | None):
    """Open the spreadsheet (imports gspread lazily)."""
    import gspread

    raw = service_account or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise SheetError("missing service-account credentials")
    if os.path.exists(raw):
        client = gspread.service_account(filename=raw)
    else:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError:
            raise SheetError("GOOGLE_SERVICE_ACCOUNT_JSON is neither a file nor JSON")
        client = gspread.service_account_from_dict(info)
    return client.open_by_key(sheet_id)


def pull_overrides(sheet_id: str, service_account: str | None) -> list[dict]:
    sheet = open_sheet(sheet_id, service_account)
    tab = sheet.worksheet(OVERRIDES_TAB)
    rows = tab.get_all_values()
    if not rows:
        return []
    return parse_override_rows(rows[1:])


def push_mirror(sheet_id: str, service_account: str | None, schedule: dict) -> int:
    sheet = open_sheet(sheet_id, service_account)
    try:
        tab = sheet.worksheet(MIRROR_TAB)
    except Exception:
        tab = sheet.add_worksheet(title=MIRROR_TAB, rows=100, cols=10)
    header = ["day", "level", "group", "track", "section", "start", "end", "text", "page"]
    body = [
        [event.get(col, "") if event.get(col) is not None else "" for col in header]
        for event in schedule["events"]
    ]
    tab.clear()
    tab.update([header] + body)
    return len(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync mirror/overrides with Google Sheets")
    parser.add_argument("--sheet-id", default=os.environ.get("SHEET_ID", ""))
    parser.add_argument("--service-account", default=None)
    parser.add_argument("--schedule", default="data/schedule.json")
    parser.add_argument("--overrides-out", default="data/overrides.json")
    parser.add_argument("--mirror-only", action="store_true")
    args = parser.parse_args(argv)

    if not args.sheet_id:
        print("ERROR: missing --sheet-id (or SHEET_ID env)", file=sys.stderr)
        return 1
    try:
        schedule = json.loads(Path(args.schedule).read_text(encoding="utf-8"))
        pushed = push_mirror(args.sheet_id, args.service_account, schedule)
        print(f"OK: mirror updated ({pushed} events)")
        if not args.mirror_only:
            overrides = pull_overrides(args.sheet_id, args.service_account)
            out = Path(args.overrides_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps({"overrides": overrides}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"OK: pulled {len(overrides)} override(s) -> {args.overrides_out}")
    except (SheetError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
