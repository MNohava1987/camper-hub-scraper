# Architect Brief — Camper Hub GCP Migration

**Current Step**: 1 — Repo Setup
**Status**: Ready for Bob

---

## Step 1 — Repo Setup

- Create a new GitHub repo (name to confirm with Project Owner — suggest `camper-hub`)
- Establish directory structure per `CLOUD_MIGRATION.md §4`
- Copy existing scraper code from `scraper/` into repo under `scraper/`
- Copy existing photo server from Pi reference (see `CLOUD_MIGRATION.md §2`) into `photo-server/`
- Copy Three Man Team files (agents/, handoff/, CLAUDE.md) into repo root
- Commit as "Initial commit — baseline state before cloud migration"
- No source code changes in this step — this is a file organization step only

**Flag**: Do not modify any Pi files. Do not start Terraform. Do not write any application code.
**Flag**: The repo baseline is a snapshot of current working state — it must represent what's running on the Pi today, not future state.

**Definition of Done**:
- [ ] GitHub repo exists with correct structure
- [ ] All existing code committed unmodified
- [ ] Three Man Team files in repo root
- [ ] `git log` shows single clean initial commit

---

## Builder Plan

[Bob writes plan here before coding]

**Arch approval**: [ ] Approved / [ ] Redirect
