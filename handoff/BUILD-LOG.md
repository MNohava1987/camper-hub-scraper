# Build Log — Camper Hub GCP Migration

**Arch owns this file. Bob updates status fields when steps complete.**
**Full migration spec: CLOUD_MIGRATION.md**

---

## Current Status

- **Active Step**: 8 — Cleanup (optional)
- **Last Completed**: Step 7 — Cutover (2026-04-02)
- **Pi Status**: Live, running from GCS, fully operational
- **Deploy Readiness**: Migration complete — all steps done

---

## Step History

### Step 1 — Repo Setup
**Status**: Complete
**Goal**: Create GitHub repo, commit all current Pi module files and scraper code as baseline, establish directory structure per CLOUD_MIGRATION.md §4.
**Files to touch**: repo root only — no source code changes
**Key decisions**:
- Repo name TBD by Project Owner
- Three Man Team files (agents/, handoff/, CLAUDE.md) go in repo root
**Reviewer**: —
**Deployed**: —

---

### Step 2 — Terraform Bootstrap
**Status**: Complete — 2026-04-02
**Goal**: Write all .tf files (provider, variables, GCS buckets, SAs, WIF bindings, AR repo, budget alert). `terraform init` + `terraform plan` clean. Apply creates buckets and IAM — no Cloud Run yet.
**Files to touch**: `infra/`
**Key decisions**: See CLOUD_MIGRATION.md §5
**Flags**:
- `camper-hub-tf-state` GCS bucket must be created MANUALLY before `terraform init`
- WIF pool/provider already exist — reference via data source, do not recreate
- billing_account_id required from Project Owner
**Reviewer**: —
**Deployed**: —

---

### Step 3 — Photo Server Adaptation
**Status**: Complete — 2026-04-02
**Deployed**: https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app
**Tested**: /manage (200), /qr.png (valid PNG), upload working
**Goal**: Adapt `photo-server/server.py` to write/read from GCS instead of local disk. Dockerfile. Build image. Deploy to Cloud Run. Test upload + manage + /qr.png.
**Files to touch**: `photo-server/`
**Key decisions**: See CLOUD_MIGRATION.md §6.1
**Flags**:
- Upload token auth required (X-Upload-Token header)
- GCS_PHOTOS_BUCKET env var injected by TF
- /qr.png must encode Cloud Run URL (not localhost)
**Reviewer**: —
**Deployed**: —

---

### Step 4 — Scraper Adaptation
**Status**: Complete — 2026-04-02
**Deployed**: Cloud Run Job camper-hub-scraper (us-central1)
**Tested**: Manual execution succeeded; events.json, kamp_dels.ics, next_weekend.json in gs://drift-command-camper-hub-data/
**Goal**: Add `OUTPUT_MODE=gcs` branch to `scraper/writer.py`. Build image. Deploy Cloud Run Job. Execute manually. Verify next_weekend.json lands in GCS data bucket.
**Files to touch**: `scraper/writer.py`, `scraper/requirements.txt`, `Dockerfile.scraper`
**Key decisions**: See CLOUD_MIGRATION.md §6.2
**Flags**:
- SCP logic stays in entrypoint.sh for local dev — only skip when OUTPUT_MODE=gcs
- Playwright + Chromium unchanged
**Reviewer**: —
**Deployed**: —

---

### Step 5 — Pi Sync Setup
**Status**: Complete — 2026-04-02
**Deployed**: pi/sync.sh committed. handoff/PI-INSTALL-INSTRUCTIONS.md written. Awaiting Project Owner to run on Pi.
**Goal**: Write `pi/sync.sh`. Document cron entry. Do NOT run on Pi yet — deliver script and instructions only. Pi SA key creation documented but not deployed.
**Files to touch**: `pi/sync.sh`, `pi/README.md`
**Key decisions**: See CLOUD_MIGRATION.md §6.3
**Flags**: Script is delivered to repo. Actual Pi installation is Step 6 and requires Project Owner go-ahead.
**Reviewer**: —
**Deployed**: —

---

### Step 6 — End-to-End Validation
**Status**: Complete — 2026-04-02
**Done**: gcloud installed on Pi, pi-sync SA activated, sync.sh installed, cron wired, manual sync verified (7 photos + data files)
**Goal**: Install sync.sh on Pi. Run manually. Upload photo via Cloud Run. Verify it appears in Pi slideshow within 5 min. Run scraper job. Verify KampDels data updates. Confirm budget alert wired.
**Files to touch**: Pi (sync.sh + cron only — no MM2 or config changes)
**Key decisions**: First step that touches the Pi. Requires explicit Project Owner go-ahead.
**Reviewer**: —
**Deployed**: —

---

### Step 7 — Cutover
**Status**: Complete — 2026-04-02
**Done**: config.js line 104 updated to Cloud Run URL, MM2 restarted. Old photo server still in autostart (Step 8 cleanup).
**Goal**: Update Pi config.js QR code URL. Remove photo-upload server from Pi autostart. Set Cloud Scheduler active. Verify QR on display routes to Cloud Run.
**Files to touch**: Pi `config.js`, Pi `~/.config/openbox/autostart`, Cloud Scheduler enabled
**Key decisions**: POINT OF NO RETURN for photo server. Project Owner must say "go" explicitly.
**Reviewer**: —
**Deployed**: —

---

### Step 8 — Cleanup
**Status**: Pending
**Goal**: Remove photo-upload/ from Pi. Remove SCP logic from entrypoint.sh. Archive local docker-compose scraper setup.
**Files to touch**: Pi (destructive removals), repo cleanup
**Key decisions**: Only after Step 7 validated for 1 week
**Reviewer**: —
**Deployed**: —

---

## Known Gaps

- Cloud Scheduler timezone: currently set to America/Chicago — confirm with Project Owner
- Upload token management: how token gets rotated if compromised — deferred to post-launch
- GCS photo lifecycle rule: 365 days — confirm this is acceptable
- Ollama LLM fallback in scraper: only works locally, not in Cloud Run — deferred

---

## Architecture Decisions (locked)

- Pi remains fully operational until Step 7 — no Pi changes in Steps 1–5
- Sync strategy: gsutil rsync on Pi cron (not push from Cloud Run) — keeps Pi pull-only
- Photo bucket: uniform_bucket_level_access = true, no public object access — serve via signed URLs or Cloud Run proxy
- TF state: GCS backend, versioning enabled
- WIF: existing pool/provider reused — no new pool created
- Upload auth: X-Upload-Token header, token stored in Secret Manager
