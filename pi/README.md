# Pi Setup — Camper Hub Sync

These files install the GCS sync job on the Pi. See `handoff/PI-INSTALL-INSTRUCTIONS.md` for the full step-by-step install process.

## What it does

`sync.sh` runs every 5 minutes via cron and:
1. Mirrors `gs://drift-command-camper-hub-photos` → `~/MagicMirror/modules/MMM-ImageSlideshow/photos/`
2. Copies `next_weekend.json` and `events.json` from `gs://drift-command-camper-hub-data` → `~/camper-hub/data/`

## Files

| File | Purpose |
|---|---|
| `sync.sh` | The cron script |
| `README.md` | This file |

## Prerequisites

- `gsutil` (part of Google Cloud SDK) installed on the Pi
- Authenticated as the `camper-hub-pi-sync` service account
- Cron entry installed (see PI-INSTALL-INSTRUCTIONS.md)
