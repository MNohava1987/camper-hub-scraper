# Pi Install Instructions — Step 6

**Prerequisites**: Pi is live at 100.108.167.28. These are the exact commands to run on the Pi as `mnohava`.

---

## What this installs

1. Google Cloud SDK (`gcloud` + `gsutil`) — if not already present
2. Authenticates as the `camper-hub-pi-sync` service account
3. Installs `pi/sync.sh` to `~/sync.sh`
4. Adds cron entry (every 5 min)
5. Runs sync manually to verify

---

## Step-by-step

### 1. SSH into the Pi
```bash
ssh mnohava@100.108.167.28
```

### 2. Check if gcloud is already installed
```bash
which gcloud && gcloud version || echo "NOT INSTALLED"
```

If not installed, install it:
```bash
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-arm.tar.gz
tar -xf google-cloud-cli-linux-arm.tar.gz
./google-cloud-sdk/install.sh --quiet
source ~/.bashrc
```

> **Note**: Use the ARM build — Pi is ARM. If the Pi is a Pi 4 or Pi 5 use the arm link above.
> Pi 3: same link works (ARMv7 compatible).

### 3. Create the pi-sync service account key

**Run this on your local machine (not the Pi):**
```bash
gcloud iam service-accounts keys create /tmp/camper-hub-pi-sync-key.json \
  --iam-account camper-hub-pi-sync@drift-command.iam.gserviceaccount.com \
  --project drift-command
```

Then copy the key to the Pi:
```bash
scp /tmp/camper-hub-pi-sync-key.json mnohava@100.108.167.28:~/camper-hub-pi-sync-key.json
rm /tmp/camper-hub-pi-sync-key.json  # remove local copy
```

### 4. Activate the service account on the Pi
```bash
# On the Pi:
gcloud auth activate-service-account \
  camper-hub-pi-sync@drift-command.iam.gserviceaccount.com \
  --key-file=/home/mnohava/camper-hub-pi-sync-key.json

# Verify
gcloud auth list
```

Expected output: `camper-hub-pi-sync@drift-command.iam.gserviceaccount.com` listed as ACTIVE.

### 5. Install sync.sh
```bash
# On the Pi:
curl -fsSL \
  https://raw.githubusercontent.com/MNohava1987/camper-hub-scraper/main/pi/sync.sh \
  -o /home/mnohava/sync.sh
chmod +x /home/mnohava/sync.sh
```

### 6. Run sync manually — verify it works
```bash
/home/mnohava/sync.sh
```

Expected output:
```
Building synchronization state...
...
photos synced to ~/MagicMirror/modules/MMM-ImageSlideshow/photos/
...
Copying gs://drift-command-camper-hub-data/next_weekend.json...
Copying gs://drift-command-camper-hub-data/events.json...
```

Verify files arrived:
```bash
ls ~/MagicMirror/modules/MMM-ImageSlideshow/photos/
cat ~/camper-hub/data/next_weekend.json | head -5
```

### 7. Add cron entry
```bash
crontab -e
```

Add this line at the bottom:
```
*/5 * * * * /home/mnohava/sync.sh >> /home/mnohava/sync.log 2>&1
```

Save and exit. Verify:
```bash
crontab -l | grep sync
```

### 8. Test upload a photo via QR code

On your phone, open the camera and scan the QR code at:
```
https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app/qr.png
```

Or open the manage page directly:
```
https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app/manage?token=y7mE_4JZweMRzmZ_nGEgfISuKrOMSxz_2i8Y5Nt-hOU
```

Upload a test photo. Wait up to 5 minutes for cron sync to fire, then check:
```bash
ls ~/MagicMirror/modules/MMM-ImageSlideshow/photos/
```

Photo should appear.

---

## Validation Checklist

- [ ] `gcloud auth list` shows pi-sync SA as ACTIVE
- [ ] Manual `sync.sh` run completes without errors
- [ ] Files appear in `~/MagicMirror/modules/MMM-ImageSlideshow/photos/`
- [ ] `next_weekend.json` and `events.json` in `~/camper-hub/data/`
- [ ] Cron entry shows in `crontab -l`
- [ ] Test photo uploaded and synced to Pi within 5 min

When all items are checked, **report back to Arch** so Step 7 (Cutover — MM2 config change) can be authorized.

---

## Rollback

If something goes wrong:
- The Pi's existing photos and data are untouched (sync only adds/replaces, MagicMirror still works from local cache)
- Remove cron entry with `crontab -e`
- Delete `~/sync.sh`
- The Pi continues operating exactly as before

---

## Key Values

| Item | Value |
|---|---|
| Photo server URL | `https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app` |
| Manage page | `https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app/manage?token=y7mE_4JZweMRzmZ_nGEgfISuKrOMSxz_2i8Y5Nt-hOU` |
| QR code | `https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app/qr.png` |
| Photos bucket | `gs://drift-command-camper-hub-photos` |
| Data bucket | `gs://drift-command-camper-hub-data` |
| Pi-sync SA | `camper-hub-pi-sync@drift-command.iam.gserviceaccount.com` |
