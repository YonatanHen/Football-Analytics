# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Backend**: FastAPI + PyMongo (Python 3.12), runs on port 8000
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS, runs on port 5173
- **Database**: MongoDB 7 (`football_analytics` db)
- **Scraping**: botasaurus + Chrome (inside Docker) for Sofascore; Tor is present but Sofascore's Cloudflare 403s it, so Chrome scrapes run without the Tor proxy

## Running the project

```bash
# Full stack (recommended)
docker compose up

# Backend only (local dev, from backend/)
uvicorn app.main:app --reload

# Frontend only (local dev, from frontend/)
npm run dev
```

Required env file: `secrets.env` in project root (loaded by Docker). Backend also reads `.env` for local dev. Key variables: `MONGO_URI`, `CORS_ORIGINS`.

## Tests

```bash
# Run all backend tests (from backend/)
pytest

# Run a single test file
pytest tests/domain/test_scoring_engine.py

# Run a single test
pytest tests/domain/test_scoring_engine.py::test_name
```

Tests use `mongomock` — no real MongoDB needed. Fixtures are in `backend/tests/conftest.py`.

No frontend tests currently.

## DB snapshots

Run inside the backend container (or locally with the stack up):

```bash
python scripts/DB/snapshot_dump.py          # -> backend/snapshots/cl-2025-2026.json
python scripts/DB/snapshot_load.py          # restore from that file
```

Always take a snapshot before implementing a new feature.

## Architecture

### Backend layers

```
app/
  api/          # FastAPI routers — thin HTTP layer only
    fetch.py    # POST /v1/fetch/ — triggers data fetch; GET /v1/fetch/status; GET /v1/fetch/cooldown
    players.py  # GET /v1/players, GET /v1/players/{id}
    analysis.py # GET /v1/analysis/scatter
  modes/        # Strategy pattern
    base.py     # AnalysisMode ABC: fetch_data(), process()
    factory.py  # ModeFactory.create("fantasy")
    fantasy.py  # FantasyMode — live Sofascore fetch
    fetch_runner.py  # Shared orchestration: run tasks, log to fetch_log
  domain/       # Pure business logic, no I/O
    models.py         # PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores
    scoring_engine.py
    sleeper_detector.py
    player_assembler.py  # build_player(), merge(), aggregate_stats()
    fetch_cooldown.py    # cooldown_status() — pure time computation for the 24h fetch limit
    competitions.py      # canonical_competition() — normalizes competition names
  infrastructure/
    mongo_repository.py   # All MongoDB I/O; serializes/deserializes domain models
    sofascore_client.py   # Fetches from Sofascore via ScraperFC (Chrome/botasaurus)
    text_utils.py         # normalize_text() for name/team fuzzy matching
  config.py        # Pydantic Settings (env vars); includes fetch_cooldown_hours (default 24)
  dependencies.py  # FastAPI DI: get_repo(), get_mode_factory()
  logging_config.py
  main.py          # App wiring: lifespan, CORS, router registration
```

### Data flow

**Fantasy mode** (live fetch): `POST /v1/fetch/` → `FantasyMode.fetch_data()` → fetches from Sofascore per competition → `player_assembler.build_player()` → scores via `ScoringEngine` → upserts to MongoDB.

**Read path**: `GET /v1/players` → `MongoRepository.get_players()` → paginates + filters by position/team/nationality/sleeper_flag.

### MongoDB collections

- `player_bios` — one doc per player (identity/bio: `name`, `norm_name`, `sofascore_player_id`, `position`, `nationality`, `photo_url`). Indexed on `sofascore_player_id` (sparse unique) and `norm_name`.
- `player_stats` — one doc per `(player_bio_id, season)`. Contains `competitions[]`, `aggregated_stats`, `aggregated_scores`, `team`, `low_sample_size`.
- `fetch_log` — audit trail for each `fetch_data()` call.
- `fetch_state` — singleton doc tracking `last_fetched_at` for the 24h Sofascore cooldown.

### Key domain concepts

- `position`: coarse (`GK|DF|MF|FW`); `position_exact`: raw string (`CB`, `RW`, etc.)
- `s_final`: composite fantasy score, primary sort key
- `sleeper_flag` / `sleeper_ratio`: `HIGH_VALUE` or `OVERPERFORMING` from `SleeperDetector.classify()`; gated on `minutes > 450`
- `low_sample_size`: true when `aggregated_stats.minutes < 90`
- Fetch cooldown: Sofascore league fetches are rate-limited to once per 24h per competition (configurable via `fetch_cooldown_hours` in `config.py`)

### Frontend pages

- `Rankings` — paginated player table with position/team filter
- `PlayerDetail` — single player view by Sofascore ID (modal; also opens for players without a Sofascore ID)
- `Compare` — side-by-side exactly 2 players
- `Sleepers` — filtered to sleeper_flag players
- `ScatterPage` — xG+xA vs G+A scatter plot via Recharts
- `LoadData` — dedicated tab for triggering `POST /v1/fetch/`; shows per-task progress, cooldown countdown, and competition selector

### Data-analyst subagent

`.claude/agents/data-analyst.md` — invoke for: chart design (Recharts/Plotly), MongoDB query design, scoring math review, sleeper threshold validation, per-90 analysis. It is read-only on the DB and does not mutate data.

### Adding a new mode

1. Create `backend/app/modes/your_mode.py` implementing `AnalysisMode`
2. Register it in `ModeFactory.create()` in `factory.py`
3. Add to `FetchRequest` accepted values in `api/fetch.py` if needed

## Constraints

- Never pick a technology or design without consulting the user first
- No auto-fetch in the UI; all data loads are explicit user actions
- Always open a `dev/*` branch for new features or bugfixes
- Always take a DB snapshot before implementing a new feature

## Never do these

- Never work directly on master, if not mentioned explicitly otherwise.
- Never commit & push code without testing it first.
