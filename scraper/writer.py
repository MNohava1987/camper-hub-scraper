import io
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from icalendar import Calendar, Event as ICalEvent


def _dedup_events(events: list[dict]) -> list[dict]:
    """Deduplicate events with the same date and similar title.

    Strips leading "Mon DD - " date prefixes, normalises to lowercase alphanum,
    groups by (date_start, first 12 chars), and keeps the most descriptive entry
    (prefers: has time_start > has description > longer title).
    """
    def _norm_key(e: dict) -> tuple:
        raw = e.get("title", "")
        # Strip leading "Mon DD - " date prefix
        stripped = re.sub(r'^[A-Za-z]+ \d{1,2}\s*[-–]\s*', '', raw)
        # Strip subtitle after " (", ": ", or " - " to get the base name
        base = re.split(r'\s*[(:]\s*|\s+-\s+', stripped)[0]
        norm = re.sub(r'[^a-z0-9]', '', base.lower())
        return (e.get("date_start", ""), norm)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in events:
        groups[_norm_key(e)].append(e)

    result = []
    for group in groups.values():
        best = max(
            group,
            key=lambda e: (
                bool(e.get("time_start")),
                bool(e.get("description")),
                len(e.get("title", "")),
            ),
        )
        result.append(best)

    # Preserve relative order from original list
    order = {id(e): i for i, e in enumerate(events)}
    result.sort(key=lambda e: order[id(e)])
    return result


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
    _maybe_gcs_upload(output_path, "application/octet-stream")


def write_next_weekend(events: list[dict], output_path: str) -> None:
    today = date.today()

    def weekend_friday(d: date) -> date:
        """Return the Friday of the current weekend, or the upcoming Friday."""
        wd = d.weekday()  # Mon=0 … Fri=4, Sat=5, Sun=6
        if wd >= 5:  # already in a weekend (Sat/Sun) — back up to Friday
            return d - timedelta(days=wd - 4)
        return d + timedelta(days=(4 - wd) % 7)

    def build_weekend(fri: date) -> dict:
        sun = fri + timedelta(days=2)
        evts = [
            e for e in events
            if e.get("date_start") and not e.get("recurring")
            and fri.isoformat() <= e["date_start"] <= sun.isoformat()
        ]
        return {
            "start": fri.isoformat(),
            "end": sun.isoformat(),
            "has_events": bool(evts),
            "theme": next((e for e in evts if e.get("type") == "theme_weekend"), None),
            "bands": _dedup_events([e for e in evts if e.get("type") == "band"]),
            "activities": _dedup_events([e for e in evts if e.get("type") == "activity"]),
            "other": _dedup_events([e for e in evts if e.get("type") not in ("band", "theme_weekend", "activity")]),
        }

    this_fri = weekend_friday(today)
    this_weekend = build_weekend(this_fri)

    # Scan forward week by week to find the next weekend that has events
    next_event_weekend = None
    fri = this_fri + timedelta(weeks=1)
    for _ in range(52):
        wknd = build_weekend(fri)
        if wknd["has_events"]:
            next_event_weekend = wknd
            break
        fri += timedelta(weeks=1)

    # Build deduplicated upcoming list (next 10 non-recurring events after today)
    upcoming_raw = [
        e for e in events
        if e.get("date_start") and not e.get("recurring")
        and e["date_start"] > today.isoformat()
    ]
    upcoming_raw.sort(key=lambda e: e["date_start"])
    upcoming = _dedup_events(upcoming_raw[:30])[:10]

    payload = {
        "generated": today.isoformat(),
        "this_weekend": this_weekend,
        "next_event_weekend": next_event_weekend,
        "upcoming": upcoming,
    }

    Path(output_path).write_text(json.dumps(payload, indent=2))
    print(f"  Wrote {output_path}")
    _maybe_gcs_upload(output_path, "application/json")


# ─── GCS upload helpers ────────────────────────────────────────────────────────

def _maybe_gcs_upload(local_path: str, content_type: str) -> None:
    """Upload local_path to GCS if OUTPUT_MODE=gcs is set."""
    if os.environ.get("OUTPUT_MODE") != "gcs":
        return
    bucket_name = os.environ["GCS_DATA_BUCKET"]
    blob_name = Path(local_path).name
    _gcs_upload(local_path, bucket_name, blob_name, content_type)


def gcs_upload_json(local_path: str) -> None:
    """Upload a JSON file to the data bucket unconditionally (for events.json)."""
    bucket_name = os.environ["GCS_DATA_BUCKET"]
    blob_name = Path(local_path).name
    _gcs_upload(local_path, bucket_name, blob_name, "application/json")


def _gcs_upload(local_path: str, bucket_name: str, blob_name: str, content_type: str) -> None:
    from google.cloud import storage  # lazy import — not available in local dev without the package
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    print(f"  Uploaded gs://{bucket_name}/{blob_name}")
