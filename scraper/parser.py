import json
import re
import requests

PROMPT = """You are parsing text scraped from a family campground website (Kamp Dels, Waterville MN).
Extract every event, activity, band performance, or themed weekend you can find.

For each item return a JSON object with these fields:
  title       - event name (string, required)
  date_start  - YYYY-MM-DD (string or null if unknown)
  date_end    - YYYY-MM-DD (string or null, same as date_start for single-day events)
  time_start  - HH:MM 24hr (string or null)
  time_end    - HH:MM 24hr (string or null)
  description - one sentence summary (string or null)
  type        - one of: "band" | "theme_weekend" | "activity" | "other"
  recurring   - true if this happens every week/day, false otherwise

Return ONLY a valid JSON array. No markdown fences. No explanation. No commentary.
If you find nothing, return an empty array: []

Text to parse:
{text}
"""


def parse_events_from_api(api_data: list[dict]) -> list[dict]:
    """
    Try to extract structured events directly from intercepted API JSON responses.
    Returns events if recognisable event data is found, otherwise empty list.
    """
    events = []
    event_keywords = {"event", "activity", "band", "weekend", "schedule", "title", "start", "date"}

    for item in api_data:
        data = item.get("data")
        flat = json.dumps(data).lower()
        if sum(1 for kw in event_keywords if kw in flat) >= 3:
            print(f"  [API intercept] Promising response from: {item['url'][:80]}")
            # Try common shapes
            candidates = []
            if isinstance(data, list):
                candidates = data
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list) and len(v) > 0:
                        candidates = v
                        break
            for item in candidates[:50]:
                if isinstance(item, dict):
                    title = (
                        item.get("title") or item.get("name") or
                        item.get("eventName") or item.get("summary") or ""
                    )
                    if not title:
                        continue
                    events.append({
                        "title": str(title),
                        "date_start": item.get("date") or item.get("startDate") or item.get("start_date") or item.get("start"),
                        "date_end": item.get("endDate") or item.get("end_date") or item.get("end"),
                        "time_start": item.get("time") or item.get("startTime") or item.get("start_time"),
                        "time_end": item.get("endTime") or item.get("end_time"),
                        "description": item.get("description") or item.get("details") or item.get("summary"),
                        "type": item.get("type") or item.get("category") or "other",
                        "recurring": bool(item.get("recurring") or item.get("isRecurring")),
                    })
    return events


def parse_events(text: str, model: str, ollama_host: str) -> list[dict]:
    # Trim to fit model context window (~6000 chars is safe for 1b models)
    trimmed = text[:6000]
    prompt = PROMPT.format(text=trimmed)

    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")
    except Exception as e:
        print(f"  Ollama error: {e}")
        return []

    # Extract JSON array from response (LLMs sometimes add preamble)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        print(f"  No JSON array found in response. Raw: {raw[:200]}")
        return []

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}. Raw: {raw[:200]}")
        return []
