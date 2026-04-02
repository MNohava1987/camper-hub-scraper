# Session Checkpoint

Date: 2026-04-02
Active Step: 2 → transitioning to Step 3
Step Status: Step 2 infrastructure applied, commit in progress
Pi Status: Live, untouched, fully operational

## State Summary

### Completed This Session
- **Step 1**: Repo created at https://github.com/MNohava1987/camper-hub-scraper, directory structure in place, initial commit pushed.
- **Step 2**: All GCP infra applied via Terraform. The following were created:
  - GCS buckets: `drift-command-camper-hub-photos`, `drift-command-camper-hub-data`
  - Service accounts: `camper-hub-photo-server`, `camper-hub-scraper`, `camper-hub-pi-sync`, `camper-hub-github-deploy`, `camper-hub-scheduler` (all @drift-command.iam.gserviceaccount.com)
  - IAM bindings, WIF binding for `MNohava1987/camper-hub-scraper`
  - Artifact Registry repo: `us-central1-docker.pkg.dev/drift-command/camper-hub`
  - Secret Manager secret: `camper-hub-upload-token` = `y7mE_4JZweMRzmZ_nGEgfISuKrOMSxz_2i8Y5Nt-hOU`
  - Budget alert: $10/month → mnohava@gmail.com
  - TF state bucket: `camper-hub-tf-state` (pre-created, versioning on)
  - Cloud Run service + job + Scheduler defined in TF but NOT yet applied (images don't exist yet)

### In Progress / Not Yet Done
- `.gitignore` has `.terraform.lock.hcl` wrongly excluded — need to remove that line so the lock file can be committed
- Terraform files need to be committed and pushed to GitHub
- GitHub Actions secrets/vars not yet set (needed before Step 3 CI works, but manual deploy works without them)

## Key Config (hardcoded, confirmed)
- GCP project: `drift-command`
- Region: `us-central1`
- Billing account: `01351C-85D7FC-16A4BB`
- Alert email: `mnohava@gmail.com`
- Upload token: `y7mE_4JZweMRzmZ_nGEgfISuKrOMSxz_2i8Y5Nt-hOU` (in Secret Manager + infra/environments/prod/terraform.tfvars — NOT committed)
- WIF provider full name: `projects/1053790586719/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider`
- GitHub deploy SA: `camper-hub-github-deploy@drift-command.iam.gserviceaccount.com`
- AR repo: `us-central1-docker.pkg.dev/drift-command/camper-hub`

## Terraform Auth Pattern
Terraform has no ADC configured. Use this pattern for ALL terraform commands:
```bash
cd /home/mnoha/camper-hub-scraper/infra
GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) \
GOOGLE_CLOUD_QUOTA_PROJECT=drift-command \
terraform <command> -var-file=environments/prod/terraform.tfvars
```

## Open Decisions
- Pi SSH access: no Tailscale on this machine. Step 6 (Pi sync install) requires the user to run commands on the Pi manually. The agent should write the exact commands to a handoff doc and pause at Step 6.
- Project Owner confirmed full autonomy through Steps 1-6; Step 7 (Cutover) requires explicit "go" from Project Owner.

## Next Actions (in order)

### 1. Fix .gitignore and commit TF files
```bash
# Edit .gitignore: remove the line ".terraform.lock.hcl"
cd /home/mnoha/camper-hub-scraper/infra
git add provider.tf variables.tf main.tf outputs.tf .terraform.lock.hcl environments/prod/terraform.tfvars.example
git add ../.gitignore
git -C /home/mnoha/camper-hub-scraper commit -m "Step 2: Terraform bootstrap — GCP infra created ..."
git -C /home/mnoha/camper-hub-scraper push
```

### 2. Set GitHub Actions secrets and variables
```bash
gh secret set WIF_PROVIDER --body "projects/1053790586719/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider" --repo MNohava1987/camper-hub-scraper
gh secret set DEPLOY_SA_EMAIL --body "camper-hub-github-deploy@drift-command.iam.gserviceaccount.com" --repo MNohava1987/camper-hub-scraper
gh variable set PROJECT_ID --body "drift-command" --repo MNohava1987/camper-hub-scraper
gh variable set REGION --body "us-central1" --repo MNohava1987/camper-hub-scraper
```

### 3. Write GitHub Actions workflows (.github/workflows/deploy-photo-server.yml and deploy-scraper.yml)
Per CLOUD_MIGRATION.md §7. Already have the template — use `gcloud builds submit` + `gcloud run deploy`.

### 4. Step 3 — Photo Server
- Write `photo-server/server.py` (GCS-backed, cloud-native — Pi's photo-upload/server.py is NOT accessible, write from spec)
- Write `photo-server/requirements.txt` and `photo-server/Dockerfile` (or use Dockerfile.photo-server at root)
- Build: `gcloud builds submit photo-server/ --tag us-central1-docker.pkg.dev/drift-command/camper-hub/photo-server:latest --project drift-command`
- Apply Cloud Run TF: `terraform apply -target=google_cloud_run_v2_service.photo_server -target=google_cloud_run_service_iam_member.photo_server_public`
- Test: upload photo, check GCS, check /manage, check /qr.png

### 5. Step 4 — Scraper Adaptation
- Update `scraper/writer.py`: add GCS upload branch when `OUTPUT_MODE=gcs`
- Add `google-cloud-storage` to `scraper/requirements.txt`
- Build: `gcloud builds submit . -f Dockerfile.scraper --tag us-central1-docker.pkg.dev/drift-command/camper-hub/scraper:latest --project drift-command`
- Apply Cloud Run Job TF: `terraform apply -target=google_cloud_run_v2_job.scraper -target=google_cloud_run_v2_job_iam_member.scheduler_invoker -target=google_cloud_scheduler_job.scraper_trigger`
- Test: `gcloud run jobs execute camper-hub-scraper --region us-central1 --project drift-command`
- Verify files in `drift-command-camper-hub-data` bucket

### 6. Step 5 — Pi Sync Script
- Write `pi/sync.sh` (gsutil rsync photos + cp data files)
- Write `pi/README.md` with install instructions
- Commit and push

### 7. Step 6 — Cannot be done autonomously (no Tailscale/SSH to Pi at 100.108.167.28)
- Write `handoff/PI-INSTALL-INSTRUCTIONS.md` with exact commands
- Pause and present to Project Owner

### 8. Step 7 — Cutover — STOP and get explicit "go" from Project Owner before doing anything
