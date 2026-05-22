# Design: Football Analytics — Fantasy Selection Engine v2

**Date:** 2026-05-21 (revised)
**Scope:** Fantasy League mode (v1). Scout and Match Prep modes are future phases.
**Library:** ScraperFC (Sofascore + FBref modules)
**Proxy:** Tor — routed at Docker Compose level

---

## 1. Overall Architecture

```
┌─────────────────────────────────┐     ┌──────────────────────────┐
│  Backend (Python / FastAPI)     │     │  Frontend (React)        │
│                                 │◄────│                          │
│  api/          ← thin routers   │ HTTP│  Tailwind CSS            │
│  domain/       ← pure logic     │     │  Recharts                │
│  modes/        ← strategy ptn   │     │  Vite dev server         │
│  infrastructure/ ← mongo+scrape │     │  port 5173               │
│  port 8000                      │     └──────────────────────────┘
└─────────────────────────────────┘
           │ ALL_PROXY=socks5://tor:9050
           ▼
        Tor service (port 9050)
           │
           ▼ (all external scraping routed through Tor)
     Sofascore + FBref
           │
           ▼
     MongoDB (port 27017, named volume)
```

Four Docker Compose services: `backend`, `frontend`, `mongodb`, `tor`.
All backend outbound HTTP (ScraperFC/Sofascore + FBref) routes through Tor automatically via `ALL_PROXY` env var — no code changes needed to ScraperFC.

---

## 2. Project Structure

```
football-analytics/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── competitions.yaml           ← competition list with both Sofascore + FBref names
│   └── app/
│       ├── main.py                 ← FastAPI app factory, mounts routers
│       ├── config.py               ← settings from env vars
│       ├── api/
│       │   ├── players.py          ← GET /v1/players, GET /v1/players/{id}
│       │   ├── fetch.py             ← POST /v1/fetch/
│       │   └── analysis.py         ← GET /v1/analysis/scatter
│       ├── domain/
│       │   ├── models.py           ← PlayerDTO, Score, CompetitionStats dataclasses
│       │   ├── scoring_engine.py   ← S_final formula, stateless
│       │   └── sleeper_detector.py ← Sleeper Ratio logic, stateless
│       ├── modes/
│       │   ├── base.py             ← AnalysisMode ABC
│       │   ├── factory.py          ← ModeFactory
│       │   └── fantasy.py          ← FantasyMode(AnalysisMode)
│       └── infrastructure/
│           ├── mongo_repository.py ← MongoRepository
│           ├── sofascore_client.py ← SofascoreClient (ScraperFC Sofascore module)
│           ├── fbref_client.py     ← FBrefClient (ScraperFC FBref misc stats only)
│           └── data_merger.py      ← PlayerDataMerger (merges two sources)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                 ← tab navigation shell
│       ├── api/
│       │   ├── client.ts           ← base fetch wrapper (VITE_API_URL)
│       │   ├── players.ts          ← getPlayers(), getPlayer(), getScatterData()
│       │   └── fetch.ts             ← triggerFetch()
│       ├── components/
│       │   ├── PlayerTable.tsx     ← sortable, paginated table
│       │   ├── PlayerCard.tsx      ← single player stats display
│       │   ├── FilterBar.tsx       ← position/team/nationality/sleeper_flag dropdowns
│       │   └── ScatterPlot.tsx     ← Recharts xG+xA vs G+A
│       └── pages/
│           ├── Rankings.tsx        ← FilterBar + PlayerTable + Refresh button
│           ├── PlayerDetail.tsx    ← search/select → PlayerCard
│           ├── Compare.tsx         ← multi-select up to 5 → row of PlayerCards
│           ├── Sleepers.tsx        ← players filtered by sleeper_flag
│           └── ScatterPage.tsx     ← ScatterPlot
└── mongo/
    └── init/                       ← optional seed scripts
```

---

## 3. Backend Class Structure

```
AnalysisMode (ABC)                          # modes/base.py
  ├── fetch_data() -> None                  # scrape + upsert to MongoDB
  ├── process() -> list[PlayerDTO]          # read from Mongo, apply mode logic
  └── get_mode_name() -> str

FantasyMode(AnalysisMode)                   # modes/fantasy.py
  ├── _scoring_engine: ScoringEngine
  └── _sleeper_detector: SleeperDetector

ModeFactory                                 # modes/factory.py
  └── create(mode: str) -> AnalysisMode     # "fantasy" | "scout" | "match_prep"

─── domain/ ─────────────────────────────────────────────────
PlayerDTO (dataclass)                       # shared data contract across all layers
CompetitionStats (dataclass)                # stats + scores for one competition
Score (dataclass)                           # offensive, defensive, tactical, s_final

ScoringEngine                               # stateless — no DB or scraper deps
  └── calculate(stats: CompetitionStats) -> Score

SleeperDetector                             # stateless
  └── classify(aggregated: Score, minutes: int) -> SleeperFlag
      # HIGH_VALUE | OVERPERFORMING | None

─── infrastructure/ ──────────────────────────────────────────
SofascoreClient                             # sofascore_client.py
  └── fetch(competition: str, year: str) -> DataFrame
      # calls ScraperFC Sofascore.scrape_player_league_stats()
      # returns 91 metrics: xG, xA, goals, assists, minutes, CS,
      #   cards, fouls, pk_saved, pk_scored, pk_taken, rating, etc.

FBrefClient                                 # fbref_client.py
  └── fetch_misc(competition: str, year: str) -> DataFrame
      # calls ScraperFC FBref.scrape_stats(stat_category="misc")
      # returns only: player_name, team, PKwon

PlayerDataMerger                            # data_merger.py
  └── merge(sofascore_df, fbref_df) -> DataFrame
      # joins on normalized (player_name, team)
      # PKwon fills 0 for unmatched players
      # flags low-confidence matches

MongoRepository
  ├── upsert_player(player: PlayerDTO) -> None
  └── get_players(filters: dict, season: str) -> list[PlayerDTO]
```

**Data source responsibilities:**

| Field | Source |
|-------|--------|
| goals, assists, xG, xA, minutes | Sofascore |
| clean_sheets, pk_saved, pk_scored, pk_taken | Sofascore |
| yellow_cards, red_cards, fouls_committed | Sofascore |
| rating, big_chances_created, key_passes | Sofascore |
| photo_url | Sofascore (`scrape_player_details`) |
| nationality, position_exact | Sofascore |
| **pk_won** | **FBref misc stats** |

---

## 4. Competition Config (`competitions.yaml`)

Each competition maps to both source names, since Sofascore and FBref may use different labels.
`sofascore_name` is passed to `SofascoreClient`; `fbref_name` to `FBrefClient`.

```yaml
competitions:
  - name: "England Premier League"
    sofascore_name: "England Premier League"
    fbref_name: "England Premier League"

  - name: "UEFA Champions League"
    sofascore_name: "UEFA Champions League"
    fbref_name: "UEFA Champions League"

  - name: "Spain La Liga"
    sofascore_name: "Spain La Liga"
    fbref_name: "Spain La Liga"

  # ... more competitions
```

---

## 5. Scoring Formula

From `Mathematical_Specification.md`. Applied per-competition AND on aggregated stats.
`pk_won` sourced from FBref; all other fields from Sofascore.

```
S_final = (Offensive + Defensive + Tactical) / (Minutes / 90)

Offensive = (G × w_G) + (A × w_A) + xG + xA
  Position weights:
    GK: G=10, A=5 | DF: G=6, A=4 | MF: G=5, A=3 | FW: G=4, A=3

Defensive:
  GK: (CS × 5) + (PK_saved × 5)
  DF: CS × 4
  MF/FW: 0

Tactical = (PK_won × 2) + (PK_scored/PK_taken × 5) - Y - (R × 3) - (Fc × 0.2)
  Guard: PK ratio term = 0 when PK_taken = 0
  Guard: PK_won defaults to 0 if FBref merge has no match

Sleeper Ratio = (xG + xA) / (G + A)
  > 1.2 AND Minutes > 450  → HIGH_VALUE
  < 0.8                    → OVERPERFORMING (regression risk)

Low sample size flag: Minutes < 90
```

---

## 6. REST API

All paths prefixed `/v1/`. All responses JSON with snake_case fields.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/v1/fetch/` | 201 | Trigger scrape (Sofascore + FBref) + upsert. Returns scrape log entry. |
| `GET` | `/v1/players` | 200 | All players, scored + ranked. Supports filters + pagination. |
| `GET` | `/v1/players/{player_id}` | 200 | Single player — all competition stats, scores, sleeper flag. |
| `GET` | `/v1/analysis/scatter` | 200 | xG+xA vs G+A data points, colored by position. |

**Filters on `GET /v1/players`:**
```
?position=GK|DF|MF|FW
?team=Arsenal
?nationality=England
?sleeper_flag=HIGH_VALUE|OVERPERFORMING
?season=2025-2026          ← defaults to SEASON env var value
?sort_by=s_final&order=desc
?page=1&page_size=50
```

**List response shape:**
```json
{ "data": [...], "total": 312, "page": 1, "page_size": 50 }
```

**Error shape:**
```json
{ "error": { "code": "not_found", "message": "Player not found." } }
```

Each resource has its own FastAPI router registered in `main.py`.
Input validated with Pydantic before any business logic.

---

## 7. MongoDB Schema

**Database:** `football_analytics`

**Collection: `players`** — one document per player per season.
Compound index `{ player_id: 1, season: 1 }` + single indexes on `season` and `aggregated_scores.s_final`.

```json
{
  "_id": "bukayo-saka-2025-2026",
  "player_id": "bukayo-saka",
  "name": "Bukayo Saka",
  "season": "2025-2026",
  "position": "FW",
  "position_exact": "RW",
  "team": "Arsenal",
  "nationality": "England",
  "photo_url": "https://...",
  "competitions": [
    {
      "competition": "England Premier League",
      "stats": {
        "goals": 8, "assists": 5, "xg": 6.2, "xa": 4.1,
        "minutes": 2340, "clean_sheets": 0,
        "pk_saved": 0, "pk_won": 1, "pk_scored": 1, "pk_taken": 1,
        "yellow_cards": 2, "red_cards": 0, "fouls_committed": 22,
        "rating": 7.4, "big_chances_created": 6, "key_passes": 41
      },
      "scores": {
        "offensive": 32.3, "defensive": 0.0, "tactical": 2.0, "s_final": 3.2
      }
    }
  ],
  "aggregated_stats": {
    "goals": 10, "assists": 6, "xg": 8.0, "xa": 5.2,
    "minutes": 2880, "clean_sheets": 0,
    "pk_saved": 0, "pk_won": 1, "pk_scored": 1, "pk_taken": 1,
    "yellow_cards": 2, "red_cards": 0, "fouls_committed": 27,
    "rating": 7.4, "big_chances_created": 8, "key_passes": 53
  },
  "aggregated_scores": {
    "offensive": 44.2, "defensive": 0.0, "tactical": 2.0,
    "s_final": 2.9, "sleeper_ratio": 1.28, "sleeper_flag": "HIGH_VALUE"
  },
  "low_sample_size": false,
  "last_updated": "2026-05-21T12:00:00Z"
}
```

**Collection: `scrape_log`**
```json
{
  "_id": ObjectId,
  "scraped_at": "2026-05-21T12:00:00Z",
  "season": "2025-2026",
  "competitions_scraped": ["England Premier League", "UEFA Champions League"],
  "sources": ["sofascore", "fbref"],
  "status": "success",
  "players_upserted": 312
}
```

---

## 8. Docker Compose

Four services. All backend outbound traffic routed through Tor via `ALL_PROXY`.

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - MONGO_URI=mongodb://mongodb:27017/football_analytics
      - SEASON=2025-2026
      - ALL_PROXY=socks5://tor:9050
    depends_on: [mongodb, tor]

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on: [backend]

  mongodb:
    image: mongo:7
    ports: ["27017:27017"]
    volumes: [mongo_data:/data/db]

  tor:
    image: dperson/torproxy
    ports: ["9050:9050"]
    restart: unless-stopped

volumes:
  mongo_data:
```

---

## 9. Future Considerations

- **Player pricing:** `price` field on player document, writable via API. Future `Sport5ScraperClient` writes to same endpoint. Manual UI input in v1.
- **RAG system:** MongoDB player documents will serve as the knowledge base. Keep text fields human-readable.
- **Scout mode / Match Prep mode:** Add via `ModeFactory` — new class implementing `AnalysisMode`.
- **Kubernetes:** Each Docker Compose service maps 1:1 to a K8s deployment. Backend config already env-var driven.
- **React production build:** Replace Vite dev server with nginx serving built bundle.
- **Fantasy data:** Sofascore fantasy endpoints not available via ScraperFC. Defer until a reliable source is identified.
- **Domestic cups:** FA Cup, Carabao Cup, etc. not in ScraperFC's Sofascore module. Revisit when coverage expands.
