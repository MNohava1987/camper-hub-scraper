# Session Checkpoint

Date: 2026-04-02
Active Step: 6 — waiting for Pi install validation
Step Status: Steps 3–5 complete and deployed; waiting for Project Owner to run PI-INSTALL-INSTRUCTIONS.md on Pi
Pi Status: Live, untouched, fully operational

## State Summary

### Completed This Session
- **Step 1**: Repo created at https://github.com/MNohava1987/camper-hub-scraper, initial commit pushed.
- **Step 2**: All GCP infra applied via Terraform. Committed and pushed.
- **Step 3 — Photo Server**: `photo-server/server.py` (Flask, GCS-backed), Dockerfile, requirements.txt. Built and deployed to Cloud Run. Tested: /manage (200), /qr.png (valid PNG).
- **Step 4 — Scraper GCS**: `scraper/writer.py` + `scraper/main.py` updated to upload to GCS when OUTPUT_MODE=gcs. Built and deployed to Cloud Run Job. Ran job successfully — all 3 files landed in `gs://drift-command-camper-hub-data/`.
- **Step 5 — Pi Sync**: `pi/sync.sh` and `pi/README.md` written and committed.
- **GitHub Actions**: `deploy-photo-server.yml` + `deploy-scraper.yml` + `cloudbuild.scraper.yaml` committed.
- **GitHub Secrets/Vars**: WIF_PROVIDER, DEPLOY_SA_EMAIL, PROJECT_ID, REGION all set.
- **Step 6 prep**: `handoff/PI-INSTALL-INSTRUCTIONS.md` written with exact Pi commands.

### Verified Working
- Photo server: https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app
  - /manage (200), /qr.png (valid PNG), upload working
- Scraper job: ran successfully, events.json + kamp_dels.ics + next_weekend.json in GCS data bucket
- GCS buckets: drift-command-camper-hub-photos, drift-command-camper-hub-data

## Key Config (hardcoded, confirmed)
- GCP project: `drift-command`
- Region: `us-central1`
- Photo server URL: `https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app`
- Photos bucket: `gs://drift-command-camper-hub-photos`
- Data bucket: `gs://drift-command-camper-hub-data`
- Upload token: `y7mE_4JZweMRzmZ_nGEgfISuKrOMSxz_2i8Y5Nt-hOU` (in Secret Manager + terraform.tfvars — NOT committed)
- WIF provider: `projects/1053790586719/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider`
- GitHub deploy SA: `camper-hub-github-deploy@drift-command.iam.gserviceaccount.com`
- AR repo: `us-central1-docker.pkg.dev/drift-command/camper-hub`
- Pi-sync SA: `camper-hub-pi-sync@drift-command.iam.gserviceaccount.com`

## Terraform Auth Pattern
```bash
cd /home/mnoha/camper-hub-scraper/infra
GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) \
GOOGLE_CLOUD_QUOTA_PROJECT=drift-command \
terraform <command> -var-file=environments/prod/terraform.tfvars
```

## Open Decisions
- **Step 6**: Project Owner must SSH to Pi and run `handoff/PI-INSTALL-INSTRUCTIONS.md`. Report back when all checklist items are green.
- **Step 7 (Cutover)**: Requires explicit "go" from Project Owner. Only change is updating MM2 config.js to point `MMM-CamperQR` at the Cloud Run URL instead of `localhost:3001`.

## Next Actions (in order)

### 1. Project Owner runs PI-INSTALL-INSTRUCTIONS.md on Pi
- SSH to 100.108.167.28
- Follow steps exactly
- Report back: all checklist items green or any errors

### 2. Step 7 — Cutover (STOP — need explicit "go")
Once Step 6 validated, update Pi's MM2 config.js:
```
Change: { label: "Add Photos", image: "http://localhost:3001/qr.png" }
To:     { label: "Add Photos", image: "https://camper-hub-photo-server-6wgwxo5cka-uc.a.run.app/qr.png" }
```
This is the only Pi file change needed.

### 3. Step 8 — Cleanup (after Step 7 is stable)
- Remove Pi's old `~/photo-upload/server.py` and associated autostart entry
- Decommission any local Docker containers that were running the photo server
- Archive or remove Tailscale SSH key from scraper setup
