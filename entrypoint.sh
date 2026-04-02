#!/bin/bash
set -e

PI_HOST="${PI_HOST:-mnohava@100.108.167.28}"
PI_DATA_DIR="${PI_DATA_DIR:-/home/mnohava/camper-hub/data}"

echo "=== Running scraper (schedule=${SCHEDULE:-all}) ==="
cd /app
python main.py "${SCHEDULE:-all}"

# Push output files to Pi over Tailscale
if [ -f /root/.ssh/id_ed25519 ]; then
    echo "=== Pushing output to Pi ==="
    scp -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
        /data/events.json /data/kamp_dels.ics /data/next_weekend.json \
        "${PI_HOST}:${PI_DATA_DIR}/"
    echo "Done — files pushed to ${PI_HOST}:${PI_DATA_DIR}"
else
    echo "No SSH key mounted — skipping push to Pi"
fi
