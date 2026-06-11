# Football Analytics

Fantasy-football analytics over scraped Sofascore + FBref data. See
[`CLAUDE.md`](./CLAUDE.md) for stack, architecture, and run/test instructions.

## Developer mode: league snapshots

Scraping goes through Tor and Sofascore 403-bans IPs that scrape too often. To avoid
re-scraping every session, scrape a league **once**, save a local JSON snapshot, and
reload it into the dev DB on demand. Everyday development then never touches Sofascore.

The scripts (`backend/scripts/`) and snapshot files (`backend/snapshots/`) are
**gitignored** local dev tooling.

### 1. Scrape the Champions League once

With the stack running (`docker compose up`), trigger a single-league fantasy fetch and
poll until it finishes:

```powershell
$job = Invoke-RestMethod -Method Post http://localhost:8000/v1/fetch/ `
  -ContentType application/json `
  -Body '{"mode":"fantasy","competitions":["UEFA Champions League"]}'
# poll until .status == "done" (re-run as needed):
Invoke-RestMethod http://localhost:8000/v1/fetch/status/$($job.job_id)
```

### 2. Dump the snapshot

From `backend/` (host venv; Mongo is exposed on `localhost:27017`):

```powershell
python scripts/snapshot_dump.py            # -> backend/snapshots/cl-2025-2026.json
```

Exports `player_bios` + `player_stats` + `scrape_log` as MongoDB Extended JSON,
preserving the `_id` ↔ `player_bio_id` linkage.

### 3. Reseed the dev DB without scraping

Any later session — even after `docker compose down` / `up` or wiping the collections —
restore the snapshot instead of re-scraping:

```powershell
python scripts/snapshot_load.py cl-2025-2026.json
```

This replaces the three collections with the snapshot contents. Indexes are rebuilt
automatically by the backend on startup.
