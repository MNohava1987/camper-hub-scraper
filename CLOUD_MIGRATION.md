# Camper Hub — GCP Cloud Migration Build Doc

**Status**: Pre-build reference
**Author**: Build agent use only
**Date**: 2026-04-02
**Pi Tailscale IP**: 100.108.167.28
**⚠ DO NOT touch the Pi until Section 8 (Cutover) is complete and validated.**

---

## 1. Purpose

Migrate Camper Hub infrastructure from Pi-local to GCP-backed cloud architecture.
The Pi (Raspberry Pi, MagicMirror display) remains fully operational throughout.
No Pi files are modified until the cloud stack is validated end-to-end.

---

## 2. Current Architecture (Pi-local — DO NOT BREAK)

```
[iPhone / Browser]
        │ POST /upload (port 3001, LAN)
        ▼
[Pi: ~/photo-upload/server.py]
        │ writes to
        ▼
[Pi: ~/MagicMirror/modules/MMM-ImageSlideshow/photos/]
        │ read by
        ▼
[Pi: MagicMirror² — node serveronly + Chromium kiosk]
        │ modules:
        │   MMM-ImageSlideshow (fullscreen_below)
        │   MMM-KampDels (reads ~/camper-hub/data/next_weekend.json)
        │   MMM-CamperQR (localhost:3001/qr.png + static qr_spotify.png)
        │   clock, calendar, weather x3

[Scraper host: /home/mnoha/camper-hub-scraper/]
        │ docker-compose run → Playwright scrape → events.json + next_weekend.json
        │ SCP via Tailscale SSH → Pi: ~/camper-hub/data/
        ▼
[Pi: ~/camper-hub/data/next_weekend.json, events.json, kamp_dels.ics]

[raspotify] → ALSA hw:2,0 (3.5mm jack) — system service, always on
```

### Pi services (OpenBox autostart, NOT systemd user units)
```bash
# ~/.config/openbox/autostart
xset s off; xset -dpms; xset s noblank
unclutter -idle 0.5 -root &
cd ~/MagicMirror && DISPLAY=:0 node serveronly &
sleep 8 && DISPLAY=:0 chromium-browser --kiosk --remote-debugging-port=9222 http://localhost:8080 &
sleep 3 && cd ~/photo-upload && python3 server.py &
```

### Pi directory layout (preserve exactly)
```
/home/mnohava/
├── MagicMirror/
│   ├── config/config.js                          ← MM2 config
│   └── modules/
│       ├── MMM-ImageSlideshow/
│       │   ├── MMM-ImageSlideshow.js             ← crossfade rewrite
│       │   ├── node_helper.js                    ← mtimeMs sort, 30s rescan
│       │   └── photos/                           ← LOCAL photo store (migrating to GCS)
│       ├── MMM-KampDels/
│       │   ├── MMM-KampDels.js
│       │   ├── node_helper.js                    ← reads next_weekend.json from disk
│       │   └── MMM-KampDels.css
│       └── MMM-CamperQR/
│           ├── MMM-CamperQR.js
│           └── MMM-CamperQR.css
├── photo-upload/
│   └── server.py                                 ← migrating to Cloud Run
└── camper-hub/
    └── data/
        ├── events.json
        ├── next_weekend.json                     ← migrating to GCS
        └── kamp_dels.ics
```

---

## 3. Target Architecture

```
[iPhone / Browser]
        │ HTTPS POST /upload
        ▼
[Cloud Run: camper-hub-photo-server]
        │ write to
        ▼
[GCS: camper-hub-photos bucket]
        │
        │ (Pi polls GCS or server pushes to Pi-local via sync job)
        ▼
[Pi: MMM-ImageSlideshow/photos/]   ← synced from GCS every N minutes

[Cloud Scheduler: scraper-trigger (cron)]
        │
        ▼
[Cloud Run Job: camper-hub-scraper]
        │ writes to
        ▼
[GCS: camper-hub-data bucket]
        │ next_weekend.json, events.json, kamp_dels.ics
        │
        │ (Pi polls GCS or sync job copies to ~/camper-hub/data/)
        ▼
[Pi: MMM-KampDels reads ~/camper-hub/data/next_weekend.json]  ← unchanged

[Pi: MMM-CamperQR] ← QR code points to Cloud Run photo server URL (not localhost)
[Pi: raspotify] ← unchanged, system service
[Pi: MagicMirror²] ← unchanged, node serveronly + Chromium kiosk
```

### Data sync strategy (Pi stays thin)
A lightweight sync script runs on the Pi (cron, every 5 min):
- `gsutil rsync -r gs://camper-hub-photos ~/MagicMirror/modules/MMM-ImageSlideshow/photos/`
- `gsutil cp gs://camper-hub-data/next_weekend.json ~/camper-hub/data/next_weekend.json`
- `gsutil cp gs://camper-hub-data/events.json ~/camper-hub/data/events.json`

This means MMM-KampDels and MMM-ImageSlideshow need **zero code changes** on the Pi.
Only `config.js` changes: QR code URL points to Cloud Run instead of localhost:3001.

---

## 4. GitHub Repo Structure

New unified repo: `camper-hub` (or extend existing `camper-hub-scraper`)

```
camper-hub/
├── .github/
│   └── workflows/
│       ├── deploy-photo-server.yml    ← Cloud Run deploy on push to main
│       └── deploy-scraper.yml         ← Cloud Run Job image build on push to main
├── infra/                             ← Terraform root
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── provider.tf
│   ├── modules/
│   │   ├── gcs/
│   │   ├── cloud_run/
│   │   ├── cloud_run_job/
│   │   └── scheduler/
│   └── environments/
│       └── prod/
│           ├── main.tf
│           └── terraform.tfvars
├── photo-server/                      ← migrated from Pi ~/photo-upload/
│   ├── server.py
│   ├── requirements.txt
│   └── Dockerfile
├── scraper/                           ← migrated from camper-hub-scraper/scraper/
│   ├── config.py
│   ├── main.py
│   ├── scraper.py
│   ├── parser.py
│   ├── merger.py
│   ├── writer.py
│   └── requirements.txt
├── Dockerfile.scraper
├── Dockerfile.photo-server
├── pi/                                ← Pi-side scripts (sync, config)
│   ├── sync.sh                        ← gsutil sync cron script
│   └── config.js.template             ← MM2 config with Cloud Run URLs
└── README.md
```

---

## 5. Terraform Resources

All resources in GCP project already connected via WIF to GitHub.

### 5.1 Provider and Backend

```hcl
# infra/provider.tf
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "camper-hub-tf-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

### 5.2 Variables

```hcl
# infra/variables.tf
variable "project_id"        { type = string }
variable "region"            { default = "us-central1" }
variable "alert_email"       { type = string }
variable "monthly_budget_usd" { default = 10 }
```

### 5.3 GCS Buckets

```hcl
# photos bucket
resource "google_storage_bucket" "photos" {
  name          = "${var.project_id}-camper-hub-photos"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }
}

# data bucket (scraper output)
resource "google_storage_bucket" "data" {
  name          = "${var.project_id}-camper-hub-data"
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true
}

# terraform state bucket (create manually before first tf init)
resource "google_storage_bucket" "tf_state" {
  name          = "${var.project_id}-camper-hub-tf-state"
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true
  versioning { enabled = true }
}
```

### 5.4 Service Accounts

```hcl
# Photo server SA — reads/writes photos bucket
resource "google_service_account" "photo_server" {
  account_id   = "camper-hub-photo-server"
  display_name = "Camper Hub Photo Server"
}

resource "google_storage_bucket_iam_member" "photo_server_photos_rw" {
  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.photo_server.email}"
}

# Scraper SA — writes data bucket, reads nothing else
resource "google_service_account" "scraper" {
  account_id   = "camper-hub-scraper"
  display_name = "Camper Hub Scraper"
}

resource "google_storage_bucket_iam_member" "scraper_data_rw" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.scraper.email}"
}

# Pi sync SA — reads both buckets, no write
resource "google_service_account" "pi_sync" {
  account_id   = "camper-hub-pi-sync"
  display_name = "Camper Hub Pi Sync"
}

resource "google_storage_bucket_iam_member" "pi_photos_ro" {
  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.pi_sync.email}"
}

resource "google_storage_bucket_iam_member" "pi_data_ro" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.pi_sync.email}"
}
```

### 5.5 Workload Identity Federation (WIF)

WIF pool and provider already exist and are connected to GitHub. Bind GitHub Actions
to the deploy service account:

```hcl
# WIF pool and provider — assumed pre-existing, reference by data source
data "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
}

# SA for GitHub Actions deployments
resource "google_service_account" "github_deploy" {
  account_id   = "camper-hub-github-deploy"
  display_name = "Camper Hub GitHub Actions Deploy"
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${data.google_iam_workload_identity_pool.github.name}/attribute.repository/YOUR_GITHUB_ORG/camper-hub"
}

# GitHub deploy SA needs Cloud Run admin + SA user + AR writer
resource "google_project_iam_member" "github_deploy_cloudrun" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}
```

### 5.6 Artifact Registry

```hcl
resource "google_artifact_registry_repository" "camper_hub" {
  location      = var.region
  repository_id = "camper-hub"
  format        = "DOCKER"
}
```

### 5.7 Cloud Run — Photo Server

```hcl
resource "google_cloud_run_v2_service" "photo_server" {
  name     = "camper-hub-photo-server"
  location = var.region

  template {
    service_account = google_service_account.photo_server.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/camper-hub/photo-server:latest"

      ports {
        container_port = 3001
      }

      env {
        name  = "GCS_PHOTOS_BUCKET"
        value = google_storage_bucket.photos.name
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

# Public access (upload from phone on any network)
resource "google_cloud_run_service_iam_member" "photo_server_public" {
  location = google_cloud_run_v2_service.photo_server.location
  service  = google_cloud_run_v2_service.photo_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "photo_server_url" {
  value = google_cloud_run_v2_service.photo_server.uri
}
```

> **Note**: The photo server's /upload endpoint must be protected. Add a shared secret
> header (`X-Upload-Token`) checked server-side, stored as a Secret Manager secret.
> The QR code URL encodes the token in the query string so the phone upload form pre-fills it.

### 5.8 Cloud Run Job — Scraper

```hcl
resource "google_cloud_run_v2_job" "scraper" {
  name     = "camper-hub-scraper"
  location = var.region

  template {
    template {
      service_account = google_service_account.scraper.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/camper-hub/scraper:latest"

        env {
          name  = "GCS_DATA_BUCKET"
          value = google_storage_bucket.data.name
        }
        env {
          name  = "OUTPUT_MODE"
          value = "gcs"   # scraper writer.py checks this; skips SCP when set
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }

      max_retries = 2

      timeout = "600s"
    }
  }
}
```

### 5.9 Cloud Scheduler

```hcl
resource "google_service_account" "scheduler" {
  account_id   = "camper-hub-scheduler"
  display_name = "Camper Hub Scheduler"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  location = google_cloud_run_v2_job.scraper.location
  name     = google_cloud_run_v2_job.scraper.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "scraper_trigger" {
  name      = "camper-hub-scraper-trigger"
  region    = var.region
  schedule  = "0 6 * * 1"   # Every Monday 6am UTC (adjust for your TZ)
  time_zone = "America/Chicago"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.scraper.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}
```

### 5.10 Budget Alert

```hcl
resource "google_billing_budget" "camper_hub" {
  billing_account = var.billing_account_id
  display_name    = "Camper Hub Monthly Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.name
    ]
    disable_default_iam_recipients = false
  }
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Camper Hub Alert Email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}
```

Add `billing_account_id` to variables.tf:
```hcl
variable "billing_account_id" { type = string }
```

---

## 6. Code Changes Required

### 6.1 Photo Server (server.py → Cloud Run)

**Current**: Writes to local `UPLOAD_DIR = /home/mnohava/MagicMirror/modules/MMM-ImageSlideshow/photos`
**Target**: Writes processed JPEG to GCS `camper-hub-photos` bucket

Key changes to `server.py`:
- Add `google-cloud-storage` to requirements.txt
- On upload: after PIL processing (exif_transpose → convert RGB → thumbnail 3840px → JPEG), write to GCS instead of local file
- `GET /photo/<filename>` → redirect to GCS signed URL or make bucket objects public-read
- `DELETE /photo/<filename>` → `bucket.blob(filename).delete()`
- `GET /manage` → list blobs from GCS bucket, render grid
- `GET /qr.png` → QR encodes the Cloud Run service URL (no more LAN IP detection needed)
- Remove `UPLOAD_DIR` local path dependency entirely
- Add upload token auth: check `X-Upload-Token` header (or `?token=` param for QR links)

**Dockerfile** (new, for Cloud Run):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV PORT=3001
CMD ["python3", "server.py"]
```

**requirements.txt additions**:
```
google-cloud-storage
qrcode[pil]
Pillow
pillow-heif
```

### 6.2 Scraper (Docker local → Cloud Run Job)

**Current**: `entrypoint.sh` SCPs output files to Pi via Tailscale SSH
**Target**: `writer.py` uploads to GCS when `OUTPUT_MODE=gcs`

Key changes:
- Add `google-cloud-storage` to scraper/requirements.txt
- In `writer.py`: check `os.environ.get("OUTPUT_MODE") == "gcs"` — if set, write to GCS bucket instead of local `data/` dir
- Remove SCP logic from `entrypoint.sh` for cloud mode (keep for local dev fallback)
- `main.py` entrypoint: no change needed
- Playwright + Chromium still run inside container — no change

**Dockerfile** (already exists, verify):
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scraper/ ./scraper/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
CMD ["/app/entrypoint.sh"]
```

For Cloud Run Job, `CMD` should be `["python3", "scraper/main.py"]` directly (no SCP needed in cloud mode).

### 6.3 Pi Sync Script (new, minimal)

`pi/sync.sh` — runs as cron every 5 minutes on Pi:
```bash
#!/bin/bash
# Sync photos from GCS to local slideshow directory
gsutil -m rsync -r -d \
  gs://YOUR_PROJECT_ID-camper-hub-photos \
  /home/mnohava/MagicMirror/modules/MMM-ImageSlideshow/photos/

# Sync event data from GCS
gsutil cp gs://YOUR_PROJECT_ID-camper-hub-data/next_weekend.json \
  /home/mnohava/camper-hub/data/next_weekend.json
gsutil cp gs://YOUR_PROJECT_ID-camper-hub-data/events.json \
  /home/mnohava/camper-hub/data/events.json
```

Cron entry on Pi (add via `crontab -e`):
```
*/5 * * * * /home/mnohava/sync.sh >> /home/mnohava/sync.log 2>&1
```

Pi needs `gsutil` installed and authenticated with the `pi_sync` SA key (or use Application Default Credentials via `gcloud auth`).

### 6.4 MagicMirror config.js — Only the QR Code URL Changes

**Current**:
```js
{ label: "Add Photos", image: "http://localhost:3001/qr.png" }
```

**Target** (after Cloud Run URL is known):
```js
{ label: "Add Photos", image: "https://camper-hub-photo-server-XXXX-uc.a.run.app/qr.png" }
```

This is the **only change** to Pi config until cutover. Make this change after Cloud Run validates.

---

## 7. GitHub Actions Workflows

### 7.1 Deploy Photo Server

`.github/workflows/deploy-photo-server.yml`:
```yaml
name: Deploy Photo Server
on:
  push:
    branches: [main]
    paths: [photo-server/**]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.DEPLOY_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit photo-server/ \
            --tag ${{ vars.REGION }}-docker.pkg.dev/${{ vars.PROJECT_ID }}/camper-hub/photo-server:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy camper-hub-photo-server \
            --image ${{ vars.REGION }}-docker.pkg.dev/${{ vars.PROJECT_ID }}/camper-hub/photo-server:latest \
            --region ${{ vars.REGION }} \
            --platform managed
```

### 7.2 Deploy Scraper Job

`.github/workflows/deploy-scraper.yml`:
```yaml
name: Deploy Scraper Job
on:
  push:
    branches: [main]
    paths: [scraper/**, Dockerfile.scraper]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.DEPLOY_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Build and push
        run: |
          gcloud builds submit . -f Dockerfile.scraper \
            --tag ${{ vars.REGION }}-docker.pkg.dev/${{ vars.PROJECT_ID }}/camper-hub/scraper:latest

      - name: Update Cloud Run Job
        run: |
          gcloud run jobs update camper-hub-scraper \
            --image ${{ vars.REGION }}-docker.pkg.dev/${{ vars.PROJECT_ID }}/camper-hub/scraper:latest \
            --region ${{ vars.REGION }}
```

---

## 8. Migration Steps (Pi stays intact throughout)

### Phase 1 — Repo Setup
- [ ] Create GitHub repo `camper-hub` (or rename existing `camper-hub-scraper`)
- [ ] Copy all Pi module files into repo under appropriate directories
- [ ] Copy `scraper/` code into repo
- [ ] Copy `photo-upload/server.py` into `photo-server/server.py`
- [ ] Commit initial state — this is the backup of current Pi code

### Phase 2 — Terraform Bootstrap
- [ ] Create `camper-hub-tf-state` GCS bucket manually (before first `tf init`)
- [ ] Write all `.tf` files per Section 5
- [ ] `terraform init` → `terraform plan` → review
- [ ] `terraform apply` — creates buckets, SAs, AR repo, budget alert
- [ ] **Do NOT deploy Cloud Run yet** — code not ready

### Phase 3 — Photo Server Adaptation
- [ ] Modify `photo-server/server.py` for GCS (Section 6.1)
- [ ] Test locally with `GOOGLE_APPLICATION_CREDENTIALS` pointed at photo_server SA key
- [ ] Write Dockerfile.photo-server
- [ ] Build and push image manually: `gcloud builds submit`
- [ ] Deploy Cloud Run service manually: `gcloud run deploy`
- [ ] Test: upload a photo via browser, verify it appears in GCS bucket
- [ ] Test: `/manage` page lists GCS objects
- [ ] Test: `/qr.png` returns QR encoding Cloud Run URL

### Phase 4 — Scraper Adaptation
- [ ] Add `OUTPUT_MODE=gcs` branch to `writer.py`
- [ ] Test locally with env var set, verify files land in GCS data bucket
- [ ] Build and push scraper image
- [ ] Deploy Cloud Run Job: `gcloud run jobs create camper-hub-scraper ...`
- [ ] Execute manually: `gcloud run jobs execute camper-hub-scraper`
- [ ] Verify `next_weekend.json` and `events.json` appear in GCS data bucket

### Phase 5 — Pi Sync Setup
- [ ] Install `gcloud` + `gsutil` on Pi if not present
- [ ] Create SA key for `camper-hub-pi-sync` SA, copy to Pi
- [ ] `gcloud auth activate-service-account --key-file=...` on Pi
- [ ] Write `sync.sh` per Section 6.3
- [ ] Run manually on Pi, verify photos sync to `~/MagicMirror/modules/MMM-ImageSlideshow/photos/`
- [ ] Run manually, verify `next_weekend.json` syncs to `~/camper-hub/data/`
- [ ] Add cron entry

### Phase 6 — Validation (Pi still running on localhost)
- [ ] Upload a photo via Cloud Run URL from phone → verify it appears on Pi display within 5 min
- [ ] Execute scraper job manually → verify `next_weekend.json` updates → verify KampDels module refreshes on Pi
- [ ] Confirm budget alert is wired (send test notification if possible)

### Phase 7 — Cutover
- [ ] Update Pi `config.js` QR code URL to Cloud Run URL
- [ ] Kill local `photo-upload/server.py` on Pi (remove from autostart)
- [ ] Stop running docker-compose scraper locally (remove cron if any)
- [ ] Set Cloud Scheduler job active
- [ ] Verify QR code on display routes to Cloud Run upload page
- [ ] Monitor for 1 week

### Phase 8 — Cleanup (after validation)
- [ ] Remove `photo-upload/` from Pi
- [ ] Remove old `entrypoint.sh` SCP logic
- [ ] Archive local `camper-hub-scraper` docker-compose setup

---

## 9. Environment Variables / Secrets Summary

| Secret/Var | Where | Value |
|---|---|---|
| `WIF_PROVIDER` | GitHub Actions secret | `projects/PROJECT_NUM/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `DEPLOY_SA_EMAIL` | GitHub Actions secret | `camper-hub-github-deploy@PROJECT_ID.iam.gserviceaccount.com` |
| `PROJECT_ID` | GitHub Actions var | your GCP project ID |
| `REGION` | GitHub Actions var | `us-central1` |
| `UPLOAD_TOKEN` | Secret Manager | random secret, embedded in QR code URL |
| `GCS_PHOTOS_BUCKET` | Cloud Run env | set by Terraform |
| `GCS_DATA_BUCKET` | Cloud Run Job env | set by Terraform |
| `billing_account_id` | terraform.tfvars | your GCP billing account ID |
| `alert_email` | terraform.tfvars | your email |

---

## 10. Cost Estimate (monthly)

| Resource | Estimate |
|---|---|
| Cloud Run photo server (min=0, ~few req/day) | ~$0.00 (free tier) |
| Cloud Run scraper job (~4 runs/month, 5 min each) | ~$0.10 |
| Cloud Scheduler | $0.10 (3 free/month then $0.10/job) |
| GCS photos (5 GB storage + transfers) | ~$0.11 |
| GCS data bucket (tiny) | ~$0.00 |
| Artifact Registry | ~$0.10 |
| **Total** | **< $1/month** |

Budget alert set at $10/month. Hard ceiling well above expected spend.

---

## 11. What Does NOT Change on Pi

These are frozen. The orchestration agent must not modify them:

- `~/.config/openbox/autostart` — until Phase 7 cutover
- `~/MagicMirror/modules/MMM-ImageSlideshow/MMM-ImageSlideshow.js` — crossfade logic
- `~/MagicMirror/modules/MMM-ImageSlideshow/node_helper.js` — mtimeMs sort
- `~/MagicMirror/modules/MMM-KampDels/` — all files, reads from disk path unchanged
- `~/MagicMirror/modules/MMM-CamperQR/` — all files
- `/etc/raspotify/conf` — Spotify Connect config
- `~/MagicMirror/config/config.js` — unchanged until Phase 7

The Pi remains fully self-contained and operational during the entire build phase.
