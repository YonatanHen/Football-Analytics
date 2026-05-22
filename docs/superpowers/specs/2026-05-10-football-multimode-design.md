# Design: Football Data Playground — Multi-Mode System (Fantasy v1)

**Date:** 2026-05-10
**Scope:** Fantasy League mode (v1). Scout and Match Prep modes are future phases.
**Benchmark dataset:** UEFA Champions League 2025/2026

---

## 1. Overall Architecture

```
┌─────────────────────────────────┐     ┌─────────────────────┐
│  Analysis Service (Python)      │     │  UI Service         │
│                                 │◄────│  (Gradio → React)   │
│  FastAPI                        │ HTTP│                     │
│  ModeFactory                    │     │  thin client only   │
│  FantasyMode                    │     │  no business logic  │
│    ├── ScoringEngine            │     └─────────────────────┘
│    └── SleeperDetector          │
│  MongoRepository                │
│  ScraperFCClient                │
└─────────────────────────────────┘
           │
           ▼
     MongoDB (K8s pod)
```

Three K8s deployments: `analysis-service`, `ui-service`, `mongodb`.

- The **Analysis Service** is the only component that touches MongoDB or ScraperFC.
- The **UI Service** is stateless — it only knows the REST API contract, making it replaceable with React in a future phase without touching any backend logic.
- All configuration (DB URI, season, competition) is passed via K8s ConfigMap environment variables.

---

## 2. Analysis Service — Class Structure

```
AnalysisMode (ABC)
  ├── fetch_data() -> None           # triggers scrape + upsert to MongoDB
  ├── process() -> list[PlayerDTO]   # reads from Mongo, applies mode logic
  └── get_mode_name() -> str

FantasyMode(AnalysisMode)
  ├── ScoringEngine                  # applies S_final formula + per-90 normalization
  └── SleeperDetector                # Sleeper Ratio logic + flag assignment

ModeFactory
  └── create(mode: str) -> AnalysisMode   # "fantasy" | "scout" | "match_prep"

MongoRepository
  ├── upsert_players(players: list)
  └── get_players(filters: dict) -> list

ScraperFCClient
  ├── fetch_standard_stats()         # goals, assists, xG, xA — via ScraperFC/FBref
  ├── fetch_misc_stats()             # cards, fouls, penalties
  └── merge_and_clean() -> DataFrame # merge on player slug, fill NaN with 0
```

`PlayerDTO` is a plain dataclass serving as the shared data contract between scoring logic and API responses. Future modes (Scout, Match Prep) will extend or compose it.

### Scoring Formula (from Mathematical_Specification.md)

```
S_final = (Offensive + Defensive + Tactical) / (Minutes / 90)

Offensive = (G × w_G) + (A × w_A) + xG + xA
  Weights:  GK: G=10, A=5 | DF: G=6, A=4 | MF: G=5, A=3 | FW: G=4, A=3

Defensive:  GK: (CS × 5) + (PK_saved × 5)
            DF: CS × 4
            MF/FW: 0

Tactical = (PK_won × 2) + (PK_scored/PK_taken × 5) - Y - (R × 3) - (Fc × 0.2)
  Guard: PK ratio term is 0 when PK_taken = 0 (no division by zero)

Sleeper Ratio = (xG + xA) / (G + A)
  > 1.2 AND Minutes > 450  → HIGH_VALUE sleeper
  < 0.8                    → OVERPERFORMING (regression risk)

Low sample size flag: Minutes < 90
```

---

## 3. REST API Endpoints

All responses are JSON. `player_id` is the FBref player slug (stable across scrapes).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/data/refresh` | Trigger ScraperFC scrape + upsert to MongoDB |
| `GET` | `/api/players` | All players, scored + ranked. Optional `?position=GK\|DF\|MF\|FW` |
| `GET` | `/api/players/{player_id}` | Single player card — all stats + scores + photo_url |
| `GET` | `/api/players/sleepers` | Sleeper picks + overperformer flags |
| `GET` | `/api/analysis/scatter` | xG+xA vs G+A data points for scatter plot |
| `GET` | `/api/analysis/compare?ids=a,b,c` | Up to 5 player IDs → array of player cards |

Photo URL is sourced from FBref where available; `null` otherwise. The UI handles the fallback display.

---

## 4. UI Service — Gradio Layout

Stateless Gradio app. All data fetched from Analysis Service API.

```
App (gr.Blocks)
├── Tab: Rankings
│   ├── Position filter dropdown (All / GK / DF / MF / FW)
│   ├── Ranked player table (sortable by S_final score)
│   └── "Refresh Data" button → POST /api/data/refresh
│
├── Tab: Player Card
│   ├── Search/select player
│   └── PlayerCard component:
│       ├── Title: "Bukayo Saka — FW (RW)"
│       ├── Photo (if available, else placeholder)
│       └── Stats list: Score, Goals, Assists, xG, xA, CS,
│                        Sleeper flag, Minutes, Discipline
│
├── Tab: Compare (up to 5 players)
│   ├── Multi-select dropdown (max 5)
│   └── 5 sub-tabs, each showing one PlayerCard
│
├── Tab: Sleepers
│   ├── High Value Sleepers list (Ratio > 1.2, Minutes > 450)
│   └── Overperformers list (Ratio < 0.8) — regression risk flags
│
└── Tab: xG vs Actual
    └── Plotly scatter: xG+xA (x-axis) vs G+A (y-axis)
        colored by position, hover shows player name + S_final score
```

---

## 5. MongoDB Schema

**Database:** `football_playground`

```json
Collection: players
{
  "_id": "bukayo-saka",
  "name": "Bukayo Saka",
  "position": "FW",
  "position_exact": "RW",
  "team": "Arsenal",
  "photo_url": "https://...",
  "season": "2025-2026",
  "competition": "Champions League",
  "stats": {
    "goals": 3, "assists": 2,
    "xg": 2.8, "xa": 1.9,
    "minutes": 720,
    "clean_sheets": 0,
    "pk_saved": 0, "pk_won": 1,
    "pk_scored": 0, "pk_taken": 0,
    "yellow_cards": 1, "red_cards": 0,
    "fouls_committed": 8
  },
  "scores": {
    "offensive": 18.7,
    "defensive": 0,
    "tactical": 0.8,
    "s_final": 2.43,
    "sleeper_ratio": 1.08,
    "sleeper_flag": null
  },
  "low_sample_size": false,
  "last_updated": "2026-05-10T12:00:00Z"
}

Collection: scrape_log
{
  "scraped_at": "2026-05-10T12:00:00Z",
  "status": "success",
  "players_upserted": 312
}
```

`sleeper_flag` values: `"HIGH_VALUE"` | `"OVERPERFORMING"` | `null`

---

## 6. Kubernetes Deployment

```
k8s/
├── analysis-service/
│   ├── deployment.yaml      # 1 replica, Python FastAPI container
│   └── service.yaml         # ClusterIP, port 8000
│
├── ui-service/
│   ├── deployment.yaml      # 1 replica, Gradio container
│   └── service.yaml         # LoadBalancer or NodePort, port 7860
│
├── mongodb/
│   ├── statefulset.yaml     # 1 replica, persistent volume
│   ├── service.yaml         # ClusterIP, port 27017
│   └── pvc.yaml             # PersistentVolumeClaim for data durability
│
└── configmap.yaml           # MONGO_URI, ANALYSIS_SERVICE_URL,
                             # SCRAPER_TARGET=champions_league, SEASON=2025-2026
```

---

## 7. v2 Considerations

- **Team Stats layer**: Add a `teams` MongoDB collection with home/away form, goals-from-corners rate, set-piece threat index, clean sheet streaks. Fantasy scoring context can incorporate team-level signals (e.g., boost players from teams with strong home records in upcoming fixtures).
- **Scout mode**: Player discovery across leagues, position-specific talent radar.
- **Match Prep mode**: Tactical briefing per opponent — key threats, set-piece patterns, defensive vulnerabilities.
- **React frontend**: Replace Gradio UI service with a React app consuming the same REST API contract.
