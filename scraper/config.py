import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/data")

# Schedule tags: "weekly" | "daily" | "frequent"
# "frequent" = runs on the 3x/day cron — placeholder for daily activities once found
SOURCES = [
    {
        "name": "events_calendar",
        "url": "https://kampdels.com/fun-in-the-dells/events-calendar/",
        "schedule": ["weekly", "daily"],
    },
    {
        "name": "planned_activities",
        "url": "https://kampdels.com/planned-activities/",
        "schedule": ["weekly", "daily", "frequent"],
    },
    {
        "name": "themed_weekends",
        "url": "https://kampdels.com/themed-weekends/",
        "schedule": ["weekly"],
        "optional": True,  # gracefully skip 404
    },
    {
        "name": "entertainment",
        "url": "https://kampdels.com/entertainment/",
        "schedule": ["weekly"],
        "optional": True,
    },
    # --- Placeholder: uncomment and set URL when daily activities source is found ---
    # {
    #     "name": "daily_activities",
    #     "url": "https://kampdels.com/DAILY_URL",
    #     "schedule": ["frequent"],
    # },
]
