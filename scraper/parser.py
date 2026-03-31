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
