"""Unit tests for tools/diff_schedule.py."""

from tools.diff_schedule import diff_schedules, event_key, render_report


def make_event(start="9:00", text="مادة", end="10:30", section="1", level="1"):
    return {
        "day": "السبت",
        "level": level,
        "group": "1",
        "section": section,
        "track": "",
        "start": start,
        "end": end,
        "text": text,
        "page": 1,
    }


def make_schedule(events):
    return {
        "days": ["السبت"],
        "events": events,
        "students": [],
        "pages": {"1": "السبت"},
    }


def test_identical_schedules_have_no_diff() -> None:
    schedule = make_schedule([make_event()])
    diff = diff_schedules(schedule, schedule)
    assert diff == {"added": [], "removed": [], "changed": []}
    assert "لا توجد فروقات" in render_report(diff)


def test_added_removed_changed() -> None:
    old = make_schedule(
        [make_event(start="9:00", text="قديمة"), make_event(start="10:30", text="ثابتة")]
    )
    new_events = [
        dict(make_event(start="9:00", text="قديمة"), text="معدلة"),
        dict(make_event(start="10:30", text="ثابتة")),
        dict(make_event(start="12:00", text="جديدة"), end="13:30"),
    ]
    diff = diff_schedules(old, make_schedule(new_events))
    assert [event["text"] for event in diff["added"]] == ["جديدة"]
    assert [event["text"] for event in diff["removed"]] == []
    assert len(diff["changed"]) == 1
    assert diff["changed"][0]["diffs"]["text"] == ("قديمة", "معدلة")
    report = render_report(diff)
    assert "مضافة: 1" in report and "معدلة: 1" in report


def test_removed_event_reported() -> None:
    old = make_schedule([make_event(start="9:00"), make_event(start="10:30")])
    new = make_schedule([make_event(start="9:00")])
    diff = diff_schedules(old, new)
    assert len(diff["removed"]) == 1
    assert diff["added"] == [] and diff["changed"] == []


def test_track_disambiguates_l3_sections() -> None:
    """Same section/start in two tracks must NOT be treated as one event."""
    old_l3 = dict(make_event(section="1", level="3"), group=None, track="علوم حاسب")
    new_same = dict(old_l3)
    diff = diff_schedules(make_schedule([old_l3]), make_schedule([new_same]))
    assert diff == {"added": [], "removed": [], "changed": []}
    other_track = dict(old_l3, track="نظم معلومات")
    diff = diff_schedules(make_schedule([old_l3]), make_schedule([other_track]))
    assert len(diff["added"]) == 1 and len(diff["removed"]) == 1
    assert event_key(old_l3) != event_key(other_track)
