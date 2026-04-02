# Camper Hub — Project Context & Session Router

## Project
GCP cloud migration of the Camper Hub Pi-based smart mirror system.
Full migration spec: `CLOUD_MIGRATION.md` — read it before doing anything.

**CRITICAL: The Pi is live and running. Do not touch it until Step 7 (Cutover).**

## Token Rules — Always Active

```
Is this in a skill or memory?   → Trust it. Skip the file read.
Is this speculative?            → Kill the tool call.
Can calls run in parallel?      → Parallelize them.
Output > 20 lines you won't use → Route to subagent.
About to restate what user said → Delete it.
```

Grep before Read. Never read a whole file to find one thing.
Do not re-read files already in context this session.

---

## Session Start — Every Role

1. Check `handoff/SESSION-CHECKPOINT.md` — if active and recent, that is your state.
2. Load your role file: `agents/ARCH.md` · `agents/BOB.md` · `agents/RICHARD.md`
3. If no checkpoint — Arch reads `handoff/BUILD-LOG.md` + `handoff/ARCHITECT-BRIEF.md` only.

**Project Owner role is set by the human. Do not ask.**

---

## Reference Files — On Demand Only

| File | Load when |
|---|---|
| `CLOUD_MIGRATION.md` | Arch needs it; checkpoint doesn't cover it |
| `handoff/ARCHITECT-BRIEF.md` | Bob and Richard load at task start |
| `handoff/BUILD-LOG.md` | Arch checks status; Bob updates when done |
| `handoff/REVIEW-REQUEST.md` | Richard loads at review start |
| `handoff/REVIEW-FEEDBACK.md` | Bob loads after Richard signals done |

---

## Handoff Files (all in handoff/)

- `ARCHITECT-BRIEF.md` — Arch writes, Bob reads
- `REVIEW-REQUEST.md` — Bob writes, Richard reads
- `REVIEW-FEEDBACK.md` — Richard writes, Bob reads
- `BUILD-LOG.md` — shared record, Arch owns
- `SESSION-CHECKPOINT.md` — Arch writes at session end

---

## Stack Reference

- **Infra**: Terraform (HCL), GCP (Cloud Run, Cloud Run Jobs, GCS, Cloud Scheduler, Budget, AR, WIF)
- **Photo server**: Python 3.11, Flask or HTTPServer, google-cloud-storage, Pillow, pillow-heif
- **Scraper**: Python 3.11, Playwright, google-cloud-storage
- **Pi**: MagicMirror² (Node.js), Chromium kiosk, gsutil sync, cron
- **CI/CD**: GitHub Actions, WIF already connected to GCP project
- **IaC backend**: GCS bucket for Terraform state (must be created manually before tf init)

## Pi Constraints (never violate)

- Pi user: `mnohava`, Tailscale IP: `100.108.167.28`
- Photo dir: `/home/mnohava/MagicMirror/modules/MMM-ImageSlideshow/photos/`
- Data dir: `/home/mnohava/camper-hub/data/`
- MM2 config: `/home/mnohava/MagicMirror/config/config.js`
- Pi services run from OpenBox autostart — NOT systemd user units
- Do not modify any Pi files until Step 7 is explicitly authorized by Project Owner
