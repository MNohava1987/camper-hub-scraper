def _key(event: dict) -> tuple:
    """Dedup key: normalized title + date."""
    return (
        event.get("title", "").lower().strip(),
        event.get("date_start") or "",
    )


def merge_events(existing: list[dict], new_events: list[dict]) -> list[dict]:
    """Add new events that don't already exist. Existing entries are never overwritten."""
    seen = {_key(e) for e in existing}
    added = 0
    for event in new_events:
        k = _key(event)
        if k not in seen:
            existing.append(event)
            seen.add(k)
            added += 1
    print(f"  Merged: {added} new, {len(existing) - added} already known")
    return existing
