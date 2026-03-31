#!/usr/bin/env python3
"""
Kamp Dels scraper pipeline.

Usage:
  python main.py [schedule]

  schedule: "weekly" | "daily" | "frequent" | "all" (default: all)
"""
import json
import sys
from pathlib import Path

from config import SOURCES, OLLAMA_HOST, OLLAMA_MODEL, OUTPUT_DIR
from scraper import scrape_page
from parser import parse_events
from merger import merge_events
from writer import write_ics, write_next_weekend

EVENTS_FILE = Path(OUTPUT_DIR) / "events.json"


def load_existing() -> list[dict]:
    if EVENTS_FILE.exists():
        return json.loads(EVENTS_FILE.read_text())
    return []


def main():
    schedule = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"=== Kamp Dels Scraper | schedule={schedule} ===")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    existing = load_existing()
    all_new = []

    for source in SOURCES:
        if schedule != "all" and schedule not in source["schedule"]:
            continue

        print(f"\n[{source['name']}] {source['url']}")
        try:
            text = scrape_page(source["url"])
            print(f"  Scraped {len(text)} chars")
            if len(text) < 100:
                print("  Warning: very little text — page may not have rendered")
            events = parse_events(text, OLLAMA_MODEL, OLLAMA_HOST)
            print(f"  Parsed {len(events)} events")
            all_new.extend(events)
        except Exception as e:
            if source.get("optional"):
                print(f"  Skipping optional source: {e}")
            else:
                print(f"  ERROR: {e}")
                raise

    merged = merge_events(existing, all_new)

    # Persist raw JSON (source of truth)
    EVENTS_FILE.write_text(json.dumps(merged, indent=2))
    print(f"\nSaved {len(merged)} total events → {EVENTS_FILE}")

    # Write outputs
    write_ics(merged, str(Path(OUTPUT_DIR) / "kamp_dels.ics"))
    write_next_weekend(merged, str(Path(OUTPUT_DIR) / "next_weekend.json"))

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
