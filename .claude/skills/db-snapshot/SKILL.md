---
name: db-snapshot
description: Take a snapshot of the current MongoDB dev database state on request, using backend/scripts/DB/snapshot_dump.py. Trigger when the user asks to snapshot/save/backup the DB, or before starting a new feature per CLAUDE.md ("Always take a DB snapshot before implementing a new feature").
---

# DB Snapshot

Dumps `player_bios` + `player_stats` + `fetch_log` from the dev MongoDB to a local JSON file under `backend/snapshots/` (gitignored — developer-local only, preserves `_id` linkage via BSON Extended JSON).

## Steps

### 1. Confirm the stack is up

Mongo must be reachable on `localhost:27017`:

```bash
docker compose ps --format "{{.Service}} {{.State}}"
```

If `mongodb` isn't `running`, tell the user to `docker compose up -d mongodb` (or the full stack) before proceeding — do not start it yourself without asking.

### 2. Determine the snapshot filename

- If the user gave a name, use it (append `.json` if missing).
- Otherwise, propose one based on context: current branch/feature name or a dated name (e.g. `dev-fantasy-platform-sport5.json`, `pre-rag-chat.json`), and confirm with the user before running — don't silently overwrite an existing snapshot with the same name.

### 3. Run the dump

From `backend/`, using the project's venv per CLAUDE.md:

```bash
.venv\Scripts\python scripts/DB/snapshot_dump.py <name>.json
```

Omitting `<name>.json` writes to the script's default (`cl-2025-2026.json`) — always pass an explicit name unless the user wants the default.

### 4. Report the result

Show the per-collection doc counts printed by the script and the output path (`backend/snapshots/<name>.json`). Remind the user this file is gitignored (local-only) — it is not committed or pushed.

## Restoring (reference only)

This skill only takes snapshots. To restore one later:

```bash
.venv\Scripts\python scripts/DB/snapshot_load.py <name>.json
```

Restoring **replaces** `player_bios`, `player_stats`, and `fetch_log` entirely — confirm with the user before running it, since it's destructive to current DB state.
