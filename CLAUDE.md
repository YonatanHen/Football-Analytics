# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Backend**: FastAPI + PyMongo (Python 3.12), runs on port 8000
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS, runs on port 5173
- **Database**: MongoDB 7 (`football_analytics` db)
- **Proxy**: Tor SOCKS5 proxy at `socks5://tor:9050` — all external scraping must go through this (Sofascore 403-bans bare IPs)

## Running the project

```bash
# Full stack (recommended)
docker compose up

# Backend only (local dev, from backend/)
uvicorn app.main:app --reload

# Frontend only (local dev, from frontend/)
npm run dev
```

Required env file: `secrets.env` in project root (loaded by Docker). Backend also reads `.env` for local dev. Key variables: `KAGGLE_API_KEY`, `MONGO_URI`, `CORS_ORIGINS`.

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

## Architecture

### Backend layers

```
app/
  api/          # FastAPI routers — thin HTTP layer only
    fetch.py    # POST /v1/fetch/ — triggers scrape
    players.py  # GET /v1/players, GET /v1/players/{id}
    analysis.py # GET /v1/analysis/scatter
  modes/        # Strategy pattern: FantasyMode, KaggleMode
    base.py     # AnalysisMode ABC: fetch_data(), process()
    factory.py  # ModeFactory.create("fantasy"|"kaggle")
  domain/       # Pure business logic, no I/O
    models.py   # PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores
    scoring_engine.py
    sleeper_detector.py
  infrastructure/
    mongo_repository.py   # All MongoDB I/O; serializes/deserializes domain models
    sofascore_client.py   # Scrapes Sofascore via scraperfc
    fbref_client.py       # Scrapes FBref misc stats
    kaggle_client.py      # Downloads FBref dataset from Kaggle
    data_merger.py        # Merges Sofascore + FBref DataFrames by player name
  config.py     # Pydantic Settings (env vars)
  dependencies.py # FastAPI DI: get_repo(), get_mode_factory()
  main.py       # App wiring: lifespan, CORS, router registration
```

### Data flow

**Fantasy mode** (live scrape): `POST /v1/fetch/` → `FantasyMode.fetch_data()` → scrapes Sofascore + FBref per competition → merges → scores via `ScoringEngine` → upserts `PlayerDTO` to MongoDB.

**Kaggle mode** (offline): Downloads the `merterdemir/fbref-2025-26-football-stats` Kaggle dataset as CSV → parses → upserts to MongoDB. Used for initial seeding from the UI.

**Read path**: `GET /v1/players` → `MongoRepository.get_players()` → paginates + filters by position/team/nationality/sleeper_flag.

### MongoDB collections

- `players` — one doc per `(sofascore_player_id, season)` or `(name, team, season)` for Kaggle players. Contains nested `competitions[]`, `aggregated_stats`, `aggregated_scores`.
- `scrape_log` — audit trail for each `fetch_data()` call.

### Key domain concepts

- `position`: coarse (`GK|DF|MF|FW`); `position_exact`: raw string (`CB`, `RW`, etc.)
- `s_final`: composite fantasy score, primary sort key
- `sleeper_flag`: `HIGH_VALUE` or `OVERPERFORMING` — players whose xG/xA exceeds actual output (or vice versa)
- `low_sample_size`: true when `aggregated_stats.minutes < 90`

### Frontend pages

- `Rankings` — paginated player table with position/team filter
- `PlayerDetail` — single player view by Sofascore ID
- `Compare` — side-by-side exactly 2 players
- `Sleepers` — filtered to sleeper_flag players
- `ScatterPage` — xG+xA vs G+A scatter plot via Recharts

On first load (`isEmpty === true`), `SeedPrompt` is shown — it calls `POST /v1/fetch/` with `mode: "kaggle"` to load the Kaggle dataset.

### Adding a new mode

1. Create `backend/app/modes/your_mode.py` implementing `AnalysisMode`
2. Register it in `ModeFactory.create()` in `factory.py`
3. Add to `FetchRequest` accepted values in `api/fetch.py` if needed

## Constraints

- Never pick a technology or design without consulting the user first
- All external scraping goes through rotating proxies (Tor); never hit sources from local IP
- No auto-fetch in the UI; all data loads are explicit user actions
- Compare page must always show exactly 2 players side-by-side
