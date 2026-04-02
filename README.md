# Camper Hub Scraper

GCP cloud migration of the Camper Hub Pi-based smart mirror system.

See `CLOUD_MIGRATION.md` for full migration spec.

## Layout

```
.github/workflows/   GitHub Actions: deploy photo server + scraper job
infra/               Terraform — GCP resources (GCS, Cloud Run, IAM, Scheduler, Budget)
photo-server/        Cloud Run service — photo upload/manage/QR
scraper/             Cloud Run Job — Kamp Dels event scraper
pi/                  Pi-side sync script (gsutil rsync, deployed in Step 5/6)
Dockerfile.scraper   Scraper container image
entrypoint.sh        Scraper entrypoint (local dev: also does SCP to Pi)
docker-compose.yml   Local dev runner
```

## Pi Status

The Pi is fully operational throughout Steps 1–6. No Pi files are modified until Step 7 (Cutover) with explicit Project Owner authorization.

## GCP Project

`drift-command` — `us-central1`
