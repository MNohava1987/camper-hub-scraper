#!/bin/bash
# Camper Hub — Pi sync script
# Runs every 5 minutes via cron. Pulls from GCS into local dirs used by MagicMirror.
set -euo pipefail

PHOTOS_BUCKET="drift-command-camper-hub-photos"
DATA_BUCKET="drift-command-camper-hub-data"
PHOTOS_DIR="/home/mnohava/MagicMirror/modules/MMM-ImageSlideshow/photos"
DATA_DIR="/home/mnohava/camper-hub/data"

# Sync photos (mirror: adds new, removes deleted)
gsutil -m rsync -r -d "gs://${PHOTOS_BUCKET}" "${PHOTOS_DIR}/"

# Copy event data files
gsutil cp "gs://${DATA_BUCKET}/next_weekend.json" "${DATA_DIR}/next_weekend.json"
gsutil cp "gs://${DATA_BUCKET}/events.json"       "${DATA_DIR}/events.json"
