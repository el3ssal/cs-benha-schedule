"""Diff two schedules -> a Markdown report (added / removed / changed).

The comparison key is (day, level, group, track, section, start) -- track is
mandatory, otherwise L3/L4 sections (restarting at 1 in every track) collide.
Only stdlib is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KEY_FIELDS = ("day", "level", "group", "track", "section", "start")
TRACKED_FIELDS = ("text", "end", "page")


def event_key(event: dict) -> tuple:
    return tuple(event[field] for field in KEY_FIELDS)


def describe_key(key: tuple) -> str:
    day, level, group, track, section, start = key
    cat = group if group else track
    return f"{day} / مستوى {level} / {cat} / سكشن {section} / {start}"


def diff_schedules(old: dict, new: dict) -> dict:
    """Return {'added': [...], 'removed': [...], 'changed': [...]}."""
    old_map = {event_key(event): event for event in old.get("events", [])}
    new_map = {event_key(event): event for event in new.get("events", [])}
    added = [new_map[key] for key in new_map if key not in old_map]
    removed = [old_map[key] for key in old_map if key not in new_map]
    changed = []
    for key in old_map:
        if key not in new_map:
            continue
        before, after = old_map[key], new_map[key]
        field_diffs = {
            field: (before.get(field), after.get(field))
            for field in TRACKED_FIELDS
            if before.get(field) != after.get(field)
        }
        if field_diffs:
            changed.append({"key": key, "diffs": field_diffs})
    by_start = lambda event: str(event.get("start", ""))
    added.sort(key=by_start)
    removed.sort(key=by_start)
    changed.sort(key=lambda item: str(item["key"]))
    return {"added": added, "removed": removed, "changed": changed}


def render_report(diff: dict) -> str:
    lines = ["# تقرير فروقات الجدول", ""]
    lines.append(f"- مواد مضافة: {len(diff['added'])}")
    lines.append(f"- مواد محذوفة: {len(diff['removed'])}")
    lines.append(f"- مواد معدلة: {len(diff['changed'])}")
    lines.append("")
    if diff["added"]:
        lines.append("## مضافة")
        for event in diff["added"]:
            lines.append(f"- {describe_key(event_key(event))}: {event.get('text', '')}")
        lines.append("")
    if diff["removed"]:
        lines.append("## محذوفة")
        for event in diff["removed"]:
            lines.append(f"- {describe_key(event_key(event))}: {event.get('text', '')}")
        lines.append("")
    if diff["changed"]:
        lines.append("## معدلة")
        for item in diff["changed"]:
            lines.append(f"- {describe_key(item['key'])}:")
            for field, (before, after) in item["diffs"].items():
                lines.append(f"  - {field}: {before!r} -> {after!r}")
        lines.append("")
    if not diff["added"] and not diff["removed"] and not diff["changed"]:
        lines.append("لا توجد فروقات.")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diff two schedule.json files")
    parser.add_argument("old", help="previous schedule.json")
    parser.add_argument("new", help="new schedule.json")
    parser.add_argument("--out", default="diff-report.md", help="report output path")
    args = parser.parse_args(argv)

    try:
        old = json.loads(Path(args.old).read_text(encoding="utf-8"))
        new = json.loads(Path(args.new).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    diff = diff_schedules(old, new)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(diff), encoding="utf-8")
    print(
        f"OK: +{len(diff['added'])} -{len(diff['removed'])} "
        f"~{len(diff['changed'])} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
