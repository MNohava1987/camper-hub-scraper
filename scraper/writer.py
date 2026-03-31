import json
from datetime import date, timedelta
from pathlib import Path

from icalendar import Calendar, Event as ICalEvent


def write_ics(events: list[dict], output_path: str) -> None:
    cal = Calendar()
    cal.add("prodid", "-//Camper Hub//Kamp Dels Events//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Kamp Dels")
    cal.add("x-wr-timezone", "America/Chicago")

    for e in events:
        if not e.get("date_start"):
            continue
        try:
            ev = ICalEvent()
            ev.add("summary", e["title"])
            ev.add("dtstart", date.fromisoformat(e["date_start"]))
            ev.add("dtend", date.fromisoformat(e.get("date_end") or e["date_start"]))
            if e.get("description"):
                ev.add("description", e["description"])
            if e.get("type"):
                ev.add("categories", [e["type"]])
            cal.add_component(ev)
        except Exception as ex:
            print(f"  Skipping malformed event '{e.get('title')}': {ex}")

    Path(output_path).write_bytes(cal.to_ical())
    print(f"  Wrote {output_path}")


def write_next_weekend(events: list[dict], output_path: str) -> None:
    today = date.today()
    # Next Saturday (or today if it's Saturday)
    days_ahead = (5 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_sat = today + timedelta(days=days_ahead)
    next_sun = next_sat + timedelta(days=1)

    weekend_events = [
        e for e in events
        if e.get("date_start") and (
            next_sat.isoformat() <= e["date_start"] <= next_sun.isoformat()
        )
    ]

    payload = {
        "generated": today.isoformat(),
        "weekend_start": next_sat.isoformat(),
        "weekend_end": next_sun.isoformat(),
        "bands": [e for e in weekend_events if e.get("type") == "band"],
        "theme": next(
            (e for e in weekend_events if e.get("type") == "theme_weekend"), None
        ),
        "activities": [e for e in weekend_events if e.get("type") == "activity"],
        "other": [e for e in weekend_events if e.get("type") == "other"],
    }

    Path(output_path).write_text(json.dumps(payload, indent=2))
    print(f"  Wrote {output_path}")
