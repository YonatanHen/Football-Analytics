# Football Analytics — Fantasy Selection Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack Fantasy Selection Engine that scrapes player stats from Sofascore (primary) and FBref (pk_won only), scores them using a position-adjusted formula, and exposes rankings via a FastAPI + React UI.

**Architecture:** Clean/Layered architecture (api → modes → domain → infrastructure). Domain layer is stateless (ScoringEngine, SleeperDetector). Infrastructure wraps ScraperFC and MongoDB. Modes layer (AnalysisMode ABC + ModeFactory + FantasyMode) orchestrates fetch → score → upsert. All external HTTP routes through Tor via `ALL_PROXY` env var.

**Tech Stack:** Python 3.12 / FastAPI / pymongo / ScraperFC / pandas / PyYAML / React 18 / TypeScript / Vite / Tailwind CSS 3 / Recharts / MongoDB 7 / Docker Compose / Tor (dperson/torproxy)

**Spec:** `docs/superpowers/specs/2026-05-21-football-analytics-design.md`
**Math spec:** `Mathematical_Specification.md`

---

## File Structure Map

```
football-analytics/
├── .gitignore
├── docker-compose.yml
├── competitions.yaml                         ← per-competition Sofascore+FBref name map
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                           ← FastAPI app factory
│       ├── config.py                         ← Settings (pydantic-settings, env vars)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── fetch.py                      ← POST /v1/fetch/
│       │   ├── players.py                    ← GET /v1/players, GET /v1/players/{id}
│       │   └── analysis.py                   ← GET /v1/analysis/scatter
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py                     ← Stats, Score, CompetitionEntry, AggregatedScores, PlayerDTO
│       │   ├── scoring_engine.py             ← ScoringEngine (stateless)
│       │   └── sleeper_detector.py           ← SleeperDetector (stateless)
│       ├── modes/
│       │   ├── __init__.py
│       │   ├── base.py                       ← AnalysisMode ABC
│       │   ├── factory.py                    ← ModeFactory
│       │   └── fantasy.py                    ← FantasyMode(AnalysisMode)
│       └── infrastructure/
│           ├── __init__.py
│           ├── mongo_repository.py           ← MongoRepository (pymongo)
│           ├── sofascore_client.py           ← SofascoreClient (wraps ScraperFC Sofascore)
│           ├── fbref_client.py              ← FBrefClient (wraps ScraperFC FBref misc stats)
│           └── data_merger.py               ← PlayerDataMerger (merges Sofascore + FBref)
├── backend/tests/
│   ├── conftest.py
│   ├── domain/
│   │   ├── test_scoring_engine.py
│   │   └── test_sleeper_detector.py
│   ├── infrastructure/
│   │   ├── test_mongo_repository.py
│   │   └── test_data_merger.py
│   └── api/
│       ├── test_fetch.py
│       ├── test_players.py
│       └── test_analysis.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                           ← tab navigation shell
        ├── api/
        │   ├── client.ts                     ← base fetch wrapper
        │   ├── players.ts                    ← getPlayers(), getPlayer(), getScatterData()
        │   └── fetch.ts                      ← triggerFetch()
        ├── components/
        │   ├── PlayerTable.tsx               ← sortable, paginated table
        │   ├── PlayerCard.tsx                ← single player stats display
        │   ├── FilterBar.tsx                 ← position/team/nationality/sleeper_flag dropdowns
        │   └── ScatterPlot.tsx               ← Recharts xG+xA vs G+A
        └── pages/
            ├── Rankings.tsx
            ├── PlayerDetail.tsx
            ├── Compare.tsx
            ├── Sleepers.tsx
            └── ScatterPage.tsx
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/domain/__init__.py` (empty)
- Create: `backend/app/modes/__init__.py` (empty)
- Create: `backend/app/infrastructure/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/domain/__init__.py` (empty)
- Create: `backend/tests/infrastructure/__init__.py` (empty)
- Create: `backend/tests/api/__init__.py` (empty)
- Create: `frontend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Init git repo**

```bash
cd C:\Users\yonat\projects\Football-Analytics
git init
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
.venv/
venv/
node_modules/
dist/
.DS_Store
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - MONGO_URI=mongodb://mongodb:27017/football_analytics
      - SEASON=2025-2026
      - ALL_PROXY=socks5://tor:9050
      - COMPETITIONS_FILE=/app/competitions.yaml
    depends_on: [mongodb, tor]
    volumes:
      - ./backend:/app
      - ./competitions.yaml:/app/competitions.yaml
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on: [backend]
    volumes:
      - ./frontend:/app
      - /app/node_modules

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

- [ ] **Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pymongo==4.10.1
scraperfc
pandas>=2.2.0
pyyaml==6.0.2
pydantic-settings==2.6.1
mongomock==4.2.0
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.0
```

- [ ] **Step 6: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

- [ ] **Step 7: Create `frontend/package.json`**

```json
{
  "name": "football-analytics-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.13.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.15",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

- [ ] **Step 8: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 9: Create `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 10: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
})
```

- [ ] **Step 11: Create `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 12: Create `frontend/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 13: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Football Analytics</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 14: Create `frontend/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 15: Create `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 16: Create all empty `__init__.py` files**

```bash
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/domain/__init__.py
touch backend/app/modes/__init__.py
touch backend/app/infrastructure/__init__.py
touch backend/tests/__init__.py
touch backend/tests/domain/__init__.py
touch backend/tests/infrastructure/__init__.py
touch backend/tests/api/__init__.py
```

- [ ] **Step 17: Commit**

```bash
git add .
git commit -m "chore: scaffold project structure"
```

---

## Task 2: Domain Models

**Files:**
- Create: `backend/app/domain/models.py`

- [ ] **Step 1: Create `backend/app/domain/models.py`**

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Stats:
    goals: int = 0
    assists: int = 0
    xg: float = 0.0
    xa: float = 0.0
    minutes: int = 0
    clean_sheets: int = 0
    pk_saved: int = 0
    pk_won: int = 0
    pk_scored: int = 0
    pk_taken: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    fouls_committed: float = 0.0
    rating: float = 0.0
    big_chances_created: int = 0
    key_passes: int = 0


@dataclass
class Score:
    offensive: float
    defensive: float
    tactical: float
    s_final: float


@dataclass
class CompetitionEntry:
    competition: str
    stats: Stats
    scores: Score


@dataclass
class AggregatedScores:
    offensive: float
    defensive: float
    tactical: float
    s_final: float
    sleeper_ratio: Optional[float]
    sleeper_flag: Optional[str]  # "HIGH_VALUE" | "OVERPERFORMING" | None


@dataclass
class PlayerDTO:
    player_id: str          # Sofascore numeric ID (str) — unique, collision-safe
    name: str
    season: str             # "2025-2026"
    position: str           # GK | DF | MF | FW (mapped from raw position string)
    position_exact: str     # raw position from Sofascore e.g. "RW", "CB"
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionEntry]
    aggregated_stats: Stats
    aggregated_scores: AggregatedScores
    low_sample_size: bool   # True when aggregated minutes < 90
    last_updated: str       # ISO 8601 UTC
```

- [ ] **Step 2: Verify models import cleanly**

```bash
cd backend && python -c "from app.domain.models import PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domain/models.py
git commit -m "feat: add domain models (Stats, Score, CompetitionEntry, PlayerDTO)"
```

---

## Task 3: ScoringEngine (TDD)

**Files:**
- Create: `backend/app/domain/scoring_engine.py`
- Create: `backend/tests/domain/test_scoring_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/domain/test_scoring_engine.py
import pytest
from app.domain.models import Stats
from app.domain.scoring_engine import ScoringEngine


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


def test_forward_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = engine.calculate(stats, "FW")
    # 5*4 + 3*3 + 4.0 + 2.5 = 20 + 9 + 6.5 = 35.5
    assert score.offensive == pytest.approx(35.5)


def test_midfielder_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=3, assists=5, xg=2.5, xa=4.0, minutes=900)
    score = engine.calculate(stats, "MF")
    # 3*5 + 5*3 + 2.5 + 4.0 = 15 + 15 + 6.5 = 36.5
    assert score.offensive == pytest.approx(36.5)


def test_defender_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=2, assists=1, xg=1.5, xa=0.5, minutes=900)
    score = engine.calculate(stats, "DF")
    # 2*6 + 1*4 + 1.5 + 0.5 = 12 + 4 + 2 = 18.0
    assert score.offensive == pytest.approx(18.0)


def test_goalkeeper_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=0, assists=1, xg=0.1, xa=0.2, minutes=900)
    score = engine.calculate(stats, "GK")
    # 0*10 + 1*5 + 0.1 + 0.2 = 5.3
    assert score.offensive == pytest.approx(5.3)


def test_goalkeeper_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=2, minutes=900)
    score = engine.calculate(stats, "GK")
    # 5*5 + 2*5 = 25 + 10 = 35
    assert score.defensive == pytest.approx(35.0)


def test_defender_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=3, minutes=900)
    score = engine.calculate(stats, "DF")
    # 3*4 = 12
    assert score.defensive == pytest.approx(12.0)


def test_midfielder_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = engine.calculate(stats, "MF")
    assert score.defensive == pytest.approx(0.0)


def test_forward_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = engine.calculate(stats, "FW")
    assert score.defensive == pytest.approx(0.0)


def test_tactical_full(engine: ScoringEngine) -> None:
    stats = Stats(
        pk_won=2, pk_scored=3, pk_taken=4,
        yellow_cards=2, red_cards=1, fouls_committed=10,
        minutes=900,
    )
    score = engine.calculate(stats, "FW")
    # pk_ratio = 3/4 * 5 = 3.75
    # tactical = 2*2 + 3.75 - 2 - 1*3 - 10*0.2 = 4 + 3.75 - 2 - 3 - 2 = 0.75
    assert score.tactical == pytest.approx(0.75)


def test_tactical_pk_ratio_zero_when_no_pk_taken(engine: ScoringEngine) -> None:
    stats = Stats(pk_scored=0, pk_taken=0, minutes=900)
    score = engine.calculate(stats, "FW")
    # pk_ratio term = 0 (guard: pk_taken == 0)
    assert score.tactical == pytest.approx(0.0)


def test_s_final_normalized_by_90_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=90)
    score = engine.calculate(stats, "FW")
    # offensive = 1*4 = 4, defensive = 0, tactical = 0
    # s_final = 4 / (90/90) = 4.0
    assert score.s_final == pytest.approx(4.0)


def test_s_final_half_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=45)
    score = engine.calculate(stats, "FW")
    # s_final = 4 / (45/90) = 4 / 0.5 = 8.0
    assert score.s_final == pytest.approx(8.0)


def test_s_final_zero_when_no_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, minutes=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(0.0)
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd backend && python -m pytest tests/domain/test_scoring_engine.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError` on `scoring_engine`

- [ ] **Step 3: Implement `backend/app/domain/scoring_engine.py`**

```python
from app.domain.models import Stats, Score

_POSITION_WEIGHTS: dict[str, dict[str, int]] = {
    "GK": {"goals": 10, "assists": 5},
    "DF": {"goals": 6, "assists": 4},
    "MF": {"goals": 5, "assists": 3},
    "FW": {"goals": 4, "assists": 3},
}


class ScoringEngine:
    def calculate(self, stats: Stats, position: str) -> Score:
        weights = _POSITION_WEIGHTS[position]
        offensive = (
            stats.goals * weights["goals"]
            + stats.assists * weights["assists"]
            + stats.xg
            + stats.xa
        )

        if position == "GK":
            defensive = stats.clean_sheets * 5.0 + stats.pk_saved * 5.0
        elif position == "DF":
            defensive = stats.clean_sheets * 4.0
        else:
            defensive = 0.0

        pk_ratio = (stats.pk_scored / stats.pk_taken * 5) if stats.pk_taken > 0 else 0.0
        tactical = (
            stats.pk_won * 2
            + pk_ratio
            - stats.yellow_cards
            - stats.red_cards * 3
            - stats.fouls_committed * 0.2
        )

        minutes_per_90 = stats.minutes / 90
        s_final = (offensive + defensive + tactical) / minutes_per_90 if minutes_per_90 > 0 else 0.0

        return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=s_final)
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
cd backend && python -m pytest tests/domain/test_scoring_engine.py -v
```

Expected: All 13 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/scoring_engine.py backend/tests/domain/test_scoring_engine.py
git commit -m "feat: implement ScoringEngine with TDD"
```

---

## Task 4: SleeperDetector (TDD)

**Files:**
- Create: `backend/app/domain/sleeper_detector.py`
- Create: `backend/tests/domain/test_sleeper_detector.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/domain/test_sleeper_detector.py
import pytest
from app.domain.sleeper_detector import SleeperDetector


@pytest.fixture
def detector() -> SleeperDetector:
    return SleeperDetector()


def test_high_value_sleeper(detector: SleeperDetector) -> None:
    # ratio = (2.0+1.5)/(1+0) = 3.5 > 1.2, minutes > 450
    result = detector.classify(xg=2.0, xa=1.5, goals=1, assists=0, minutes=500)
    assert result == "HIGH_VALUE"


def test_high_value_requires_more_than_450_minutes(detector: SleeperDetector) -> None:
    # ratio > 1.2 but minutes = 450 (not > 450)
    result = detector.classify(xg=2.0, xa=1.5, goals=1, assists=0, minutes=450)
    assert result is None


def test_overperforming(detector: SleeperDetector) -> None:
    # ratio = (0.5+0.2)/(3+1) = 0.175 < 0.8
    result = detector.classify(xg=0.5, xa=0.2, goals=3, assists=1, minutes=800)
    assert result == "OVERPERFORMING"


def test_no_flag_when_ratio_in_range(detector: SleeperDetector) -> None:
    # ratio = (1.0+0.5)/(1+0) = 1.5... wait, that's > 1.2
    # use ratio exactly 1.0: (1.0+0.0)/(1+0) = 1.0, 0.8 <= 1.0 <= 1.2
    result = detector.classify(xg=1.0, xa=0.0, goals=1, assists=0, minutes=900)
    assert result is None


def test_zero_output_with_xg_and_enough_minutes(detector: SleeperDetector) -> None:
    # 0 goals + 0 assists but has xg+xa — treat as infinite ratio → HIGH_VALUE if minutes > 450
    result = detector.classify(xg=1.0, xa=0.5, goals=0, assists=0, minutes=500)
    assert result == "HIGH_VALUE"


def test_zero_output_with_xg_but_not_enough_minutes(detector: SleeperDetector) -> None:
    result = detector.classify(xg=1.0, xa=0.5, goals=0, assists=0, minutes=300)
    assert result is None


def test_zero_everything_returns_none(detector: SleeperDetector) -> None:
    result = detector.classify(xg=0.0, xa=0.0, goals=0, assists=0, minutes=500)
    assert result is None


def test_get_ratio_returns_none_when_no_output(detector: SleeperDetector) -> None:
    assert detector.get_ratio(xg=1.0, xa=0.5, goals=0, assists=0) is None


def test_get_ratio_calculates_correctly(detector: SleeperDetector) -> None:
    # (2.0 + 1.0) / (1 + 2) = 1.0
    assert detector.get_ratio(xg=2.0, xa=1.0, goals=1, assists=2) == pytest.approx(1.0)
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd backend && python -m pytest tests/domain/test_sleeper_detector.py -v 2>&1 | head -5
```

Expected: `ImportError` on `sleeper_detector`

- [ ] **Step 3: Implement `backend/app/domain/sleeper_detector.py`**

```python
from typing import Optional


class SleeperDetector:
    def classify(
        self, xg: float, xa: float, goals: int, assists: int, minutes: int
    ) -> Optional[str]:
        total_output = goals + assists
        if total_output == 0:
            if (xg + xa) > 0 and minutes > 450:
                return "HIGH_VALUE"
            return None
        ratio = (xg + xa) / total_output
        if ratio > 1.2 and minutes > 450:
            return "HIGH_VALUE"
        if ratio < 0.8:
            return "OVERPERFORMING"
        return None

    def get_ratio(
        self, xg: float, xa: float, goals: int, assists: int
    ) -> Optional[float]:
        total = goals + assists
        if total == 0:
            return None
        return round((xg + xa) / total, 4)
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
cd backend && python -m pytest tests/domain/test_sleeper_detector.py -v
```

Expected: All 9 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/sleeper_detector.py backend/tests/domain/test_sleeper_detector.py
git commit -m "feat: implement SleeperDetector with TDD"
```

---

## Task 5: Config, competitions.yaml, and conftest

**Files:**
- Create: `backend/app/config.py`
- Create: `competitions.yaml`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017/football_analytics"
    season: str = "2025-2026"
    competitions_file: str = "competitions.yaml"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 2: Create `competitions.yaml` in project root**

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

  - name: "Germany Bundesliga"
    sofascore_name: "Germany Bundesliga"
    fbref_name: "Germany Bundesliga"

  - name: "Italy Serie A"
    sofascore_name: "Italy Serie A"
    fbref_name: "Italy Serie A"

  - name: "France Ligue 1"
    sofascore_name: "France Ligue 1"
    fbref_name: "France Ligue 1"
```

- [ ] **Step 3: Create `backend/tests/conftest.py`**

```python
import pytest
import mongomock
from pymongo import MongoClient
from app.infrastructure.mongo_repository import MongoRepository


@pytest.fixture
def mongo_client() -> MongoClient:
    return mongomock.MongoClient()


@pytest.fixture
def repo(mongo_client: MongoClient) -> MongoRepository:
    return MongoRepository(mongo_client)
```

- [ ] **Step 4: Verify config loads**

```bash
cd backend && python -c "from app.config import settings; print(settings.season)"
```

Expected: `2025-2026`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py competitions.yaml backend/tests/conftest.py
git commit -m "feat: add config, competitions.yaml, and test conftest"
```

---

## Task 6: MongoRepository (TDD)

**Files:**
- Create: `backend/app/infrastructure/mongo_repository.py`
- Create: `backend/tests/infrastructure/test_mongo_repository.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/infrastructure/test_mongo_repository.py
import pytest
from datetime import datetime, timezone
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.infrastructure.mongo_repository import MongoRepository


def _make_player(player_id: str = "123", season: str = "2025-2026") -> PlayerDTO:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = Score(offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06)
    return PlayerDTO(
        player_id=player_id,
        name="Test Player",
        season=season,
        position="FW",
        position_exact="ST",
        team="Arsenal",
        nationality="England",
        photo_url="https://example.com/photo.jpg",
        competitions=[CompetitionEntry(competition="England Premier League", stats=stats, scores=score)],
        aggregated_stats=stats,
        aggregated_scores=AggregatedScores(
            offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06,
            sleeper_ratio=1.3, sleeper_flag="HIGH_VALUE",
        ),
        low_sample_size=False,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


def test_upsert_and_get_player(repo: MongoRepository) -> None:
    player = _make_player("123", "2025-2026")
    repo.upsert_player(player)
    result = repo.get_player("123", "2025-2026")
    assert result is not None
    assert result.player_id == "123"
    assert result.name == "Test Player"
    assert result.aggregated_stats.goals == 5
    assert result.aggregated_scores.sleeper_flag == "HIGH_VALUE"


def test_upsert_overwrites_existing(repo: MongoRepository) -> None:
    player = _make_player("123", "2025-2026")
    repo.upsert_player(player)
    updated = _make_player("123", "2025-2026")
    updated.name = "Updated Name"
    repo.upsert_player(updated)
    result = repo.get_player("123", "2025-2026")
    assert result is not None
    assert result.name == "Updated Name"


def test_get_player_not_found_returns_none(repo: MongoRepository) -> None:
    result = repo.get_player("nonexistent", "2025-2026")
    assert result is None


def test_get_players_filter_by_position(repo: MongoRepository) -> None:
    fw = _make_player("1", "2025-2026")
    gk = _make_player("2", "2025-2026")
    gk.position = "GK"
    repo.upsert_player(fw)
    repo.upsert_player(gk)
    players, total = repo.get_players(season="2025-2026", position="GK")
    assert total == 1
    assert players[0].player_id == "2"


def test_get_players_filter_by_team(repo: MongoRepository) -> None:
    player = _make_player("1", "2025-2026")
    repo.upsert_player(player)
    players, total = repo.get_players(season="2025-2026", team="Arsenal")
    assert total == 1
    players_other, total_other = repo.get_players(season="2025-2026", team="Chelsea")
    assert total_other == 0


def test_get_players_filter_by_sleeper_flag(repo: MongoRepository) -> None:
    player = _make_player("1", "2025-2026")
    repo.upsert_player(player)
    players, total = repo.get_players(season="2025-2026", sleeper_flag="HIGH_VALUE")
    assert total == 1
    players_none, total_none = repo.get_players(season="2025-2026", sleeper_flag="OVERPERFORMING")
    assert total_none == 0


def test_get_players_pagination(repo: MongoRepository) -> None:
    for i in range(5):
        p = _make_player(str(i), "2025-2026")
        repo.upsert_player(p)
    players, total = repo.get_players(season="2025-2026", page=1, page_size=3)
    assert total == 5
    assert len(players) == 3


def test_get_players_separate_seasons(repo: MongoRepository) -> None:
    p1 = _make_player("1", "2025-2026")
    p2 = _make_player("1", "2024-2025")
    repo.upsert_player(p1)
    repo.upsert_player(p2)
    players_2526, total = repo.get_players(season="2025-2026")
    assert total == 1
    players_2425, total2 = repo.get_players(season="2024-2025")
    assert total2 == 1


def test_log_scrape(repo: MongoRepository) -> None:
    entry = repo.log_scrape(
        season="2025-2026",
        competitions=["England Premier League"],
        players_upserted=42,
        status="success",
    )
    assert entry["players_upserted"] == 42
    assert entry["status"] == "success"
    assert "_id" in entry


def test_get_scatter_data(repo: MongoRepository) -> None:
    player = _make_player("1", "2025-2026")
    repo.upsert_player(player)
    data = repo.get_scatter_data("2025-2026")
    assert len(data) == 1
    assert "name" in data[0]
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd backend && python -m pytest tests/infrastructure/test_mongo_repository.py -v 2>&1 | head -5
```

Expected: `ImportError` on `mongo_repository`

- [ ] **Step 3: Implement `backend/app/infrastructure/mongo_repository.py`**

```python
from typing import Optional
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)


def _stats_to_dict(stats: Stats) -> dict:
    return {
        "goals": stats.goals, "assists": stats.assists,
        "xg": stats.xg, "xa": stats.xa,
        "minutes": stats.minutes, "clean_sheets": stats.clean_sheets,
        "pk_saved": stats.pk_saved, "pk_won": stats.pk_won,
        "pk_scored": stats.pk_scored, "pk_taken": stats.pk_taken,
        "yellow_cards": stats.yellow_cards, "red_cards": stats.red_cards,
        "fouls_committed": stats.fouls_committed, "rating": stats.rating,
        "big_chances_created": stats.big_chances_created, "key_passes": stats.key_passes,
    }


def _stats_from_dict(d: dict) -> Stats:
    return Stats(
        goals=d.get("goals", 0), assists=d.get("assists", 0),
        xg=d.get("xg", 0.0), xa=d.get("xa", 0.0),
        minutes=d.get("minutes", 0), clean_sheets=d.get("clean_sheets", 0),
        pk_saved=d.get("pk_saved", 0), pk_won=d.get("pk_won", 0),
        pk_scored=d.get("pk_scored", 0), pk_taken=d.get("pk_taken", 0),
        yellow_cards=d.get("yellow_cards", 0), red_cards=d.get("red_cards", 0),
        fouls_committed=d.get("fouls_committed", 0.0), rating=d.get("rating", 0.0),
        big_chances_created=d.get("big_chances_created", 0), key_passes=d.get("key_passes", 0),
    )


def _player_to_doc(player: PlayerDTO) -> dict:
    return {
        "_id": f"{player.player_id}-{player.season}",
        "player_id": player.player_id,
        "name": player.name,
        "season": player.season,
        "position": player.position,
        "position_exact": player.position_exact,
        "team": player.team,
        "nationality": player.nationality,
        "photo_url": player.photo_url,
        "competitions": [
            {
                "competition": c.competition,
                "stats": _stats_to_dict(c.stats),
                "scores": {
                    "offensive": c.scores.offensive,
                    "defensive": c.scores.defensive,
                    "tactical": c.scores.tactical,
                    "s_final": c.scores.s_final,
                },
            }
            for c in player.competitions
        ],
        "aggregated_stats": _stats_to_dict(player.aggregated_stats),
        "aggregated_scores": {
            "offensive": player.aggregated_scores.offensive,
            "defensive": player.aggregated_scores.defensive,
            "tactical": player.aggregated_scores.tactical,
            "s_final": player.aggregated_scores.s_final,
            "sleeper_ratio": player.aggregated_scores.sleeper_ratio,
            "sleeper_flag": player.aggregated_scores.sleeper_flag,
        },
        "low_sample_size": player.low_sample_size,
        "last_updated": player.last_updated,
    }


def _player_from_doc(doc: dict) -> PlayerDTO:
    comps = []
    for c in doc.get("competitions", []):
        s = c["scores"]
        comps.append(CompetitionEntry(
            competition=c["competition"],
            stats=_stats_from_dict(c["stats"]),
            scores=Score(
                offensive=s["offensive"], defensive=s["defensive"],
                tactical=s["tactical"], s_final=s["s_final"],
            ),
        ))
    ag = doc["aggregated_scores"]
    return PlayerDTO(
        player_id=doc["player_id"],
        name=doc["name"],
        season=doc["season"],
        position=doc["position"],
        position_exact=doc["position_exact"],
        team=doc["team"],
        nationality=doc["nationality"],
        photo_url=doc["photo_url"],
        competitions=comps,
        aggregated_stats=_stats_from_dict(doc["aggregated_stats"]),
        aggregated_scores=AggregatedScores(
            offensive=ag["offensive"], defensive=ag["defensive"],
            tactical=ag["tactical"], s_final=ag["s_final"],
            sleeper_ratio=ag.get("sleeper_ratio"),
            sleeper_flag=ag.get("sleeper_flag"),
        ),
        low_sample_size=doc["low_sample_size"],
        last_updated=doc["last_updated"],
    )


class MongoRepository:
    def __init__(self, client: MongoClient) -> None:
        self._db = client["football_analytics"]
        self._players: Collection = self._db["players"]
        self._scrape_log: Collection = self._db["scrape_log"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._players.create_index(
            [("player_id", ASCENDING), ("season", ASCENDING)], unique=True
        )
        self._players.create_index([("season", ASCENDING)])
        self._players.create_index([("aggregated_scores.s_final", DESCENDING)])

    def upsert_player(self, player: PlayerDTO) -> None:
        doc = _player_to_doc(player)
        self._players.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def get_players(
        self,
        season: str,
        position: Optional[str] = None,
        team: Optional[str] = None,
        nationality: Optional[str] = None,
        sleeper_flag: Optional[str] = None,
        sort_by: str = "s_final",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlayerDTO], int]:
        query: dict = {"season": season}
        if position:
            query["position"] = position
        if team:
            query["team"] = team
        if nationality:
            query["nationality"] = nationality
        if sleeper_flag:
            query["aggregated_scores.sleeper_flag"] = sleeper_flag

        sort_field = f"aggregated_scores.{sort_by}" if sort_by == "s_final" else sort_by
        sort_dir = DESCENDING if order == "desc" else ASCENDING
        total = self._players.count_documents(query)
        skip = (page - 1) * page_size
        docs = list(
            self._players.find(query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(page_size)
        )
        return [_player_from_doc(d) for d in docs], total

    def get_player(self, player_id: str, season: str) -> Optional[PlayerDTO]:
        doc = self._players.find_one({"player_id": player_id, "season": season})
        return _player_from_doc(doc) if doc else None

    def get_scatter_data(self, season: str) -> list[dict]:
        projection = {
            "name": 1, "position": 1, "player_id": 1,
            "aggregated_stats.xg": 1, "aggregated_stats.xa": 1,
            "aggregated_stats.goals": 1, "aggregated_stats.assists": 1,
            "_id": 0,
        }
        return list(self._players.find({"season": season}, projection))

    def log_scrape(
        self, season: str, competitions: list[str], players_upserted: int, status: str
    ) -> dict:
        entry: dict = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "season": season,
            "competitions_scraped": competitions,
            "sources": ["sofascore", "fbref"],
            "status": status,
            "players_upserted": players_upserted,
        }
        result = self._scrape_log.insert_one(entry)
        entry["_id"] = str(result.inserted_id)
        return entry
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
cd backend && python -m pytest tests/infrastructure/test_mongo_repository.py -v
```

Expected: All 10 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/mongo_repository.py backend/tests/infrastructure/test_mongo_repository.py
git commit -m "feat: implement MongoRepository with TDD"
```

---

## Task 7: PlayerDataMerger (TDD)

**Files:**
- Create: `backend/app/infrastructure/data_merger.py`
- Create: `backend/tests/infrastructure/test_data_merger.py`

The merger joins a Sofascore DataFrame (one row per player in a competition) with a FBref DataFrame (player_name, team, PKwon). It normalizes player names and teams for fuzzy matching. `pk_won` defaults to 0 on no match.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/infrastructure/test_data_merger.py
import pandas as pd
import pytest
from app.infrastructure.data_merger import PlayerDataMerger


@pytest.fixture
def merger() -> PlayerDataMerger:
    return PlayerDataMerger()


def _sofascore_df(**kwargs: object) -> pd.DataFrame:
    defaults = {
        "player_id": "123",
        "name": "Bukayo Saka",
        "team": "Arsenal",
        "nationality": "England",
        "position": "FW",
        "position_exact": "RW",
        "photo_url": "https://example.com/photo.jpg",
        "goals": 5,
        "assists": 3,
        "xg": 4.0,
        "xa": 2.5,
        "minutes": 900,
        "clean_sheets": 0,
        "pk_saved": 0,
        "pk_scored": 1,
        "pk_taken": 1,
        "yellow_cards": 1,
        "red_cards": 0,
        "fouls_committed": 10.0,
        "rating": 7.5,
        "big_chances_created": 5,
        "key_passes": 30,
    }
    defaults.update(kwargs)
    return pd.DataFrame([defaults])


def _fbref_df(player_name: str = "Bukayo Saka", team: str = "Arsenal", pk_won: int = 2) -> pd.DataFrame:
    return pd.DataFrame([{"player_name": player_name, "team": team, "pk_won": pk_won}])


def test_merge_adds_pk_won(merger: PlayerDataMerger) -> None:
    sofascore = _sofascore_df()
    fbref = _fbref_df(pk_won=2)
    result = merger.merge(sofascore, fbref)
    assert result.iloc[0]["pk_won"] == 2


def test_merge_defaults_pk_won_to_zero_on_no_match(merger: PlayerDataMerger) -> None:
    sofascore = _sofascore_df(name="Bukayo Saka", team="Arsenal")
    fbref = _fbref_df(player_name="Mohamed Salah", team="Liverpool", pk_won=3)
    result = merger.merge(sofascore, fbref)
    assert result.iloc[0]["pk_won"] == 0


def test_merge_normalizes_names_case_insensitive(merger: PlayerDataMerger) -> None:
    sofascore = _sofascore_df(name="bukayo saka")
    fbref = _fbref_df(player_name="BUKAYO SAKA")
    result = merger.merge(sofascore, fbref)
    assert result.iloc[0]["pk_won"] == 2


def test_merge_handles_extra_whitespace(merger: PlayerDataMerger) -> None:
    sofascore = _sofascore_df(name="  Bukayo Saka  ")
    fbref = _fbref_df(player_name="Bukayo Saka")
    result = merger.merge(sofascore, fbref)
    assert result.iloc[0]["pk_won"] == 2


def test_merge_result_has_all_sofascore_columns(merger: PlayerDataMerger) -> None:
    sofascore = _sofascore_df()
    fbref = _fbref_df()
    result = merger.merge(sofascore, fbref)
    for col in ["player_id", "name", "team", "goals", "assists", "xg", "xa", "minutes"]:
        assert col in result.columns


def test_merge_multiple_players(merger: PlayerDataMerger) -> None:
    sofascore = pd.DataFrame([
        {**_sofascore_df().iloc[0].to_dict(), "player_id": "1", "name": "Player A", "team": "Arsenal"},
        {**_sofascore_df().iloc[0].to_dict(), "player_id": "2", "name": "Player B", "team": "Chelsea"},
    ])
    fbref = pd.DataFrame([
        {"player_name": "Player A", "team": "Arsenal", "pk_won": 1},
        {"player_name": "Player B", "team": "Chelsea", "pk_won": 3},
    ])
    result = merger.merge(sofascore, fbref)
    assert len(result) == 2
    assert result[result["player_id"] == "1"].iloc[0]["pk_won"] == 1
    assert result[result["player_id"] == "2"].iloc[0]["pk_won"] == 3
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd backend && python -m pytest tests/infrastructure/test_data_merger.py -v 2>&1 | head -5
```

Expected: `ImportError` on `data_merger`

- [ ] **Step 3: Implement `backend/app/infrastructure/data_merger.py`**

```python
import pandas as pd


def _normalize(s: str) -> str:
    return str(s).lower().strip()


class PlayerDataMerger:
    def merge(self, sofascore_df: pd.DataFrame, fbref_df: pd.DataFrame) -> pd.DataFrame:
        ss = sofascore_df.copy()
        fb = fbref_df.copy()

        ss["_norm_name"] = ss["name"].map(_normalize)
        ss["_norm_team"] = ss["team"].map(_normalize)
        fb["_norm_name"] = fb["player_name"].map(_normalize)
        fb["_norm_team"] = fb["team"].map(_normalize)

        fb_indexed = fb.set_index(["_norm_name", "_norm_team"])["pk_won"]

        def lookup_pk_won(row: pd.Series) -> int:
            key = (row["_norm_name"], row["_norm_team"])
            return int(fb_indexed.get(key, 0))

        ss["pk_won"] = ss.apply(lookup_pk_won, axis=1)
        ss.drop(columns=["_norm_name", "_norm_team"], inplace=True)
        return ss
```

- [ ] **Step 4: Run tests — verify they PASS**

```bash
cd backend && python -m pytest tests/infrastructure/test_data_merger.py -v
```

Expected: All 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/infrastructure/data_merger.py backend/tests/infrastructure/test_data_merger.py
git commit -m "feat: implement PlayerDataMerger with TDD"
```

---

## Task 8: SofascoreClient and FBrefClient

**Files:**
- Create: `backend/app/infrastructure/sofascore_client.py`
- Create: `backend/app/infrastructure/fbref_client.py`

These wrap ScraperFC. They are thin adapters that map ScraperFC column names to our internal standardized column names. Both return a pandas DataFrame with the columns our domain expects.

**IMPORTANT:** ScraperFC column names must be verified against actual library output before the position mapping or column renaming is finalized. The clients include a `_COLUMN_MAP` dict that should be updated if column names differ at runtime.

- [ ] **Step 1: Implement `backend/app/infrastructure/sofascore_client.py`**

```python
import pandas as pd
from scraperfc import Sofascore  # type: ignore[import]

# Maps ScraperFC column names → our internal names.
# Verify against actual ScraperFC output: run Sofascore().scrape_player_league_stats()
# and inspect df.columns to confirm these names.
_COLUMN_MAP = {
    "id": "player_id",
    "name": "name",
    "team": "team",
    "goals": "goals",
    "goalAssist": "assists",
    "expectedGoals": "xg",
    "expectedAssists": "xa",
    "minutesPlayed": "minutes",
    "cleanSheet": "clean_sheets",
    "savedPenalty": "pk_saved",
    "scoredPenalty": "pk_scored",
    "penaltyTaken": "pk_taken",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "foulCommitted": "fouls_committed",
    "rating": "rating",
    "bigChanceCreated": "big_chances_created",
    "keyPass": "key_passes",
    "playerNationalityName": "nationality",
    "playerPosition": "position_exact",
    "playerPhotoUrl": "photo_url",
}

# Maps Sofascore raw position codes → our canonical 4-category position
_POSITION_MAP: dict[str, str] = {
    "G": "GK", "GK": "GK",
    "D": "DF", "DF": "DF", "CB": "DF", "LB": "DF", "RB": "DF", "LWB": "DF", "RWB": "DF",
    "M": "MF", "MF": "MF", "CM": "MF", "DM": "MF", "AM": "MF", "LM": "MF", "RM": "MF",
    "F": "FW", "FW": "FW", "ST": "FW", "CF": "FW", "LW": "FW", "RW": "FW", "SS": "FW",
}

_NUMERIC_COLS = [
    "goals", "assists", "xg", "xa", "minutes", "clean_sheets",
    "pk_saved", "pk_scored", "pk_taken", "yellow_cards", "red_cards",
    "fouls_committed", "rating", "big_chances_created", "key_passes",
]


class SofascoreClient:
    def fetch(self, competition: str, year: int) -> pd.DataFrame:
        raw: pd.DataFrame = Sofascore().scrape_player_league_stats(competition, year)
        df = self._normalize(raw)
        return df

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        present = {k: v for k, v in _COLUMN_MAP.items() if k in raw.columns}
        df = raw.rename(columns=present)

        # Add mapped position column derived from position_exact
        if "position_exact" in df.columns:
            df["position"] = df["position_exact"].map(
                lambda p: _POSITION_MAP.get(str(p).upper(), "MF")
            )
        else:
            df["position"] = "MF"

        # Ensure player_id is a string
        if "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str)

        # Fill nulls with 0 for numeric columns
        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        for col in ["photo_url", "nationality", "position_exact"]:
            if col not in df.columns:
                df[col] = ""

        return df
```

- [ ] **Step 2: Implement `backend/app/infrastructure/fbref_client.py`**

```python
import pandas as pd
from scraperfc import FBref  # type: ignore[import]

# Maps FBref misc stat column names → our internal names.
# Verify against actual ScraperFC output: run FBref().scrape_stats("misc") and inspect columns.
_FBREF_COLUMN_MAP = {
    "Player": "player_name",
    "Squad": "team",
    "PKwon": "pk_won",
}


class FBrefClient:
    def fetch_misc(self, competition: str, year: int) -> pd.DataFrame:
        raw: pd.DataFrame = FBref().scrape_stats(competition, year, "misc")
        return self._normalize(raw)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        present = {k: v for k, v in _FBREF_COLUMN_MAP.items() if k in raw.columns}
        df = raw.rename(columns=present)

        # Keep only the columns we need
        keep = [c for c in ["player_name", "team", "pk_won"] if c in df.columns]
        df = df[keep].copy()

        if "pk_won" in df.columns:
            df["pk_won"] = df["pk_won"].fillna(0).astype(int)
        else:
            df["pk_won"] = 0

        return df
```

- [ ] **Step 3: Verify imports (no ScraperFC network call)**

```bash
cd backend && python -c "from app.infrastructure.sofascore_client import SofascoreClient; from app.infrastructure.fbref_client import FBrefClient; print('OK')"
```

Expected: `OK` (ScraperFC classes only instantiate at `.fetch()` call time)

- [ ] **Step 4: Commit**

```bash
git add backend/app/infrastructure/sofascore_client.py backend/app/infrastructure/fbref_client.py
git commit -m "feat: add SofascoreClient and FBrefClient (ScraperFC adapters)"
```

---

## Task 9: Modes Layer (AnalysisMode, ModeFactory, FantasyMode)

**Files:**
- Create: `backend/app/modes/base.py`
- Create: `backend/app/modes/factory.py`
- Create: `backend/app/modes/fantasy.py`

- [ ] **Step 1: Create `backend/app/modes/base.py`**

```python
from abc import ABC, abstractmethod
from app.domain.models import PlayerDTO


class AnalysisMode(ABC):
    @abstractmethod
    def fetch_data(self, season: str) -> None:
        """Scrape data from sources and upsert to MongoDB."""

    @abstractmethod
    def process(self, season: str) -> list[PlayerDTO]:
        """Read from MongoDB, apply mode logic, return scored players."""

    @abstractmethod
    def get_mode_name(self) -> str:
        """Return a string identifier for this mode."""
```

- [ ] **Step 2: Create `backend/app/modes/fantasy.py`**

```python
import yaml
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.domain.scoring_engine import ScoringEngine
from app.domain.sleeper_detector import SleeperDetector
from app.infrastructure.sofascore_client import SofascoreClient
from app.infrastructure.fbref_client import FBrefClient
from app.infrastructure.data_merger import PlayerDataMerger
from app.infrastructure.mongo_repository import MongoRepository

logger = logging.getLogger(__name__)


def _load_competitions(competitions_file: str) -> list[dict]:
    with open(competitions_file, "r") as f:
        data = yaml.safe_load(f)
    return data["competitions"]


def _aggregate_stats(entries: list[CompetitionEntry]) -> Stats:
    total = Stats()
    for e in entries:
        s = e.stats
        total.goals += s.goals
        total.assists += s.assists
        total.xg += s.xg
        total.xa += s.xa
        total.minutes += s.minutes
        total.clean_sheets += s.clean_sheets
        total.pk_saved += s.pk_saved
        total.pk_won += s.pk_won
        total.pk_scored += s.pk_scored
        total.pk_taken += s.pk_taken
        total.yellow_cards += s.yellow_cards
        total.red_cards += s.red_cards
        total.fouls_committed += s.fouls_committed
        # rating and big_chances_created/key_passes: use max rating, sum the rest
        total.rating = max(total.rating, s.rating)
        total.big_chances_created += s.big_chances_created
        total.key_passes += s.key_passes
    return total


class FantasyMode(AnalysisMode):
    def __init__(
        self,
        mongo_client: MongoClient,
        competitions_file: str = "competitions.yaml",
    ) -> None:
        self._repo = MongoRepository(mongo_client)
        self._scoring = ScoringEngine()
        self._sleeper = SleeperDetector()
        self._sofascore = SofascoreClient()
        self._fbref = FBrefClient()
        self._merger = PlayerDataMerger()
        self._competitions_file = competitions_file

    def get_mode_name(self) -> str:
        return "fantasy"

    def fetch_data(self, season: str) -> None:
        year = int(season.split("-")[0])
        competitions = _load_competitions(self._competitions_file)
        # player_id → list of CompetitionEntry
        player_entries: dict[str, list] = {}
        # player_id → metadata (name, team, nationality, position, position_exact, photo_url)
        player_meta: dict[str, dict] = {}

        for comp in competitions:
            ss_name = comp["sofascore_name"]
            fb_name = comp["fbref_name"]
            try:
                ss_df = self._sofascore.fetch(ss_name, year)
            except Exception as exc:
                logger.warning("Sofascore fetch failed for %s: %s", ss_name, exc)
                continue

            try:
                fb_df = self._fbref.fetch_misc(fb_name, year)
            except Exception as exc:
                logger.warning("FBref fetch failed for %s: %s", fb_name, exc)
                import pandas as pd
                fb_df = pd.DataFrame(columns=["player_name", "team", "pk_won"])

            merged = self._merger.merge(ss_df, fb_df)

            for _, row in merged.iterrows():
                pid = str(row.get("player_id", ""))
                if not pid:
                    continue

                stats = Stats(
                    goals=int(row.get("goals", 0)),
                    assists=int(row.get("assists", 0)),
                    xg=float(row.get("xg", 0.0)),
                    xa=float(row.get("xa", 0.0)),
                    minutes=int(row.get("minutes", 0)),
                    clean_sheets=int(row.get("clean_sheets", 0)),
                    pk_saved=int(row.get("pk_saved", 0)),
                    pk_won=int(row.get("pk_won", 0)),
                    pk_scored=int(row.get("pk_scored", 0)),
                    pk_taken=int(row.get("pk_taken", 0)),
                    yellow_cards=int(row.get("yellow_cards", 0)),
                    red_cards=int(row.get("red_cards", 0)),
                    fouls_committed=float(row.get("fouls_committed", 0.0)),
                    rating=float(row.get("rating", 0.0)),
                    big_chances_created=int(row.get("big_chances_created", 0)),
                    key_passes=int(row.get("key_passes", 0)),
                )
                position = str(row.get("position", "MF"))
                score = self._scoring.calculate(stats, position)
                entry = CompetitionEntry(
                    competition=comp["name"], stats=stats, scores=score
                )

                if pid not in player_entries:
                    player_entries[pid] = []
                    player_meta[pid] = {
                        "name": str(row.get("name", "")),
                        "team": str(row.get("team", "")),
                        "nationality": str(row.get("nationality", "")),
                        "position": position,
                        "position_exact": str(row.get("position_exact", "")),
                        "photo_url": str(row.get("photo_url", "")),
                    }
                player_entries[pid].append(entry)

        upserted = 0
        for pid, entries in player_entries.items():
            meta = player_meta[pid]
            agg_stats = _aggregate_stats(entries)
            agg_score = self._scoring.calculate(agg_stats, meta["position"])
            sleeper_ratio = self._sleeper.get_ratio(
                agg_stats.xg, agg_stats.xa, agg_stats.goals, agg_stats.assists
            )
            sleeper_flag = self._sleeper.classify(
                agg_stats.xg, agg_stats.xa, agg_stats.goals, agg_stats.assists, agg_stats.minutes
            )
            player = PlayerDTO(
                player_id=pid,
                name=meta["name"],
                season=season,
                position=meta["position"],
                position_exact=meta["position_exact"],
                team=meta["team"],
                nationality=meta["nationality"],
                photo_url=meta["photo_url"],
                competitions=entries,
                aggregated_stats=agg_stats,
                aggregated_scores=AggregatedScores(
                    offensive=agg_score.offensive,
                    defensive=agg_score.defensive,
                    tactical=agg_score.tactical,
                    s_final=agg_score.s_final,
                    sleeper_ratio=sleeper_ratio,
                    sleeper_flag=sleeper_flag,
                ),
                low_sample_size=agg_stats.minutes < 90,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            self._repo.upsert_player(player)
            upserted += 1

        self._repo.log_scrape(
            season=season,
            competitions=[c["name"] for c in competitions],
            players_upserted=upserted,
            status="success",
        )

    def process(self, season: str) -> list[PlayerDTO]:
        players, _ = self._repo.get_players(season=season)
        return players
```

- [ ] **Step 3: Create `backend/app/modes/factory.py`**

```python
from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.modes.fantasy import FantasyMode


class ModeFactory:
    def __init__(self, mongo_client: MongoClient, competitions_file: str) -> None:
        self._mongo_client = mongo_client
        self._competitions_file = competitions_file

    def create(self, mode: str) -> AnalysisMode:
        if mode == "fantasy":
            return FantasyMode(self._mongo_client, self._competitions_file)
        raise ValueError(f"Unknown mode: {mode!r}. Available: fantasy")
```

- [ ] **Step 4: Verify imports**

```bash
cd backend && python -c "from app.modes.factory import ModeFactory; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/modes/
git commit -m "feat: add AnalysisMode ABC, FantasyMode, and ModeFactory"
```

---

## Task 10: FastAPI App, Config, and All Routers

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/fetch.py`
- Create: `backend/app/api/players.py`
- Create: `backend/app/api/analysis.py`
- Create: `backend/tests/api/test_players.py`
- Create: `backend/tests/api/test_fetch.py`
- Create: `backend/tests/api/test_analysis.py`

- [ ] **Step 1: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from pymongo import MongoClient
from app.config import settings
from app.modes.factory import ModeFactory
from app.infrastructure.mongo_repository import MongoRepository
from app.api import fetch, players, analysis


_mongo_client: MongoClient | None = None
_mode_factory: ModeFactory | None = None
_repo: MongoRepository | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _mongo_client, _mode_factory, _repo
    _mongo_client = MongoClient(settings.mongo_uri)
    _repo = MongoRepository(_mongo_client)
    _mode_factory = ModeFactory(_mongo_client, settings.competitions_file)
    yield
    if _mongo_client:
        _mongo_client.close()


app = FastAPI(title="Football Analytics API", lifespan=lifespan)
app.include_router(fetch.router, prefix="/v1")
app.include_router(players.router, prefix="/v1")
app.include_router(analysis.router, prefix="/v1")


def get_repo() -> MongoRepository:
    assert _repo is not None
    return _repo


def get_mode_factory() -> ModeFactory:
    assert _mode_factory is not None
    return _mode_factory
```

- [ ] **Step 2: Create `backend/app/api/fetch.py`**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from app.main import get_mode_factory
from app.modes.factory import ModeFactory
from app.config import settings

router = APIRouter()


class FetchRequest(BaseModel):
    season: str | None = None
    mode: str = "fantasy"


@router.post("/fetch/", status_code=201)
def trigger_fetch(
    body: FetchRequest,
    mode_factory: ModeFactory = Depends(get_mode_factory),
) -> dict:
    season = body.season or settings.season
    mode = mode_factory.create(body.mode)
    mode.fetch_data(season)
    return {"status": "ok", "season": season, "mode": body.mode}
```

- [ ] **Step 3: Create `backend/app/api/players.py`**

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.main import get_repo
from app.infrastructure.mongo_repository import MongoRepository
from app.config import settings

router = APIRouter()


class StatsOut(BaseModel):
    goals: int
    assists: int
    xg: float
    xa: float
    minutes: int
    clean_sheets: int
    pk_saved: int
    pk_won: int
    pk_scored: int
    pk_taken: int
    yellow_cards: int
    red_cards: int
    fouls_committed: float
    rating: float
    big_chances_created: int
    key_passes: int


class ScoreOut(BaseModel):
    offensive: float
    defensive: float
    tactical: float
    s_final: float


class CompetitionOut(BaseModel):
    competition: str
    stats: StatsOut
    scores: ScoreOut


class AggregatedScoresOut(BaseModel):
    offensive: float
    defensive: float
    tactical: float
    s_final: float
    sleeper_ratio: Optional[float]
    sleeper_flag: Optional[str]


class PlayerOut(BaseModel):
    player_id: str
    name: str
    season: str
    position: str
    position_exact: str
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionOut]
    aggregated_stats: StatsOut
    aggregated_scores: AggregatedScoresOut
    low_sample_size: bool
    last_updated: str


class PlayerListOut(BaseModel):
    data: list[PlayerOut]
    total: int
    page: int
    page_size: int


def _player_to_out(p: object) -> PlayerOut:
    from app.domain.models import PlayerDTO
    assert isinstance(p, PlayerDTO)
    return PlayerOut(
        player_id=p.player_id,
        name=p.name,
        season=p.season,
        position=p.position,
        position_exact=p.position_exact,
        team=p.team,
        nationality=p.nationality,
        photo_url=p.photo_url,
        competitions=[
            CompetitionOut(
                competition=c.competition,
                stats=StatsOut(**c.stats.__dict__),
                scores=ScoreOut(**c.scores.__dict__),
            )
            for c in p.competitions
        ],
        aggregated_stats=StatsOut(**p.aggregated_stats.__dict__),
        aggregated_scores=AggregatedScoresOut(**p.aggregated_scores.__dict__),
        low_sample_size=p.low_sample_size,
        last_updated=p.last_updated,
    )


@router.get("/players", response_model=PlayerListOut)
def list_players(
    position: Optional[str] = Query(None, pattern="^(GK|DF|MF|FW)$"),
    team: Optional[str] = None,
    nationality: Optional[str] = None,
    sleeper_flag: Optional[str] = Query(None, pattern="^(HIGH_VALUE|OVERPERFORMING)$"),
    season: Optional[str] = None,
    sort_by: str = Query("s_final", pattern="^s_final$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    repo: MongoRepository = Depends(get_repo),
) -> PlayerListOut:
    resolved_season = season or settings.season
    players, total = repo.get_players(
        season=resolved_season,
        position=position,
        team=team,
        nationality=nationality,
        sleeper_flag=sleeper_flag,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return PlayerListOut(
        data=[_player_to_out(p) for p in players],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/players/{player_id}", response_model=PlayerOut)
def get_player(
    player_id: str,
    season: Optional[str] = None,
    repo: MongoRepository = Depends(get_repo),
) -> PlayerOut:
    resolved_season = season or settings.season
    player = repo.get_player(player_id, resolved_season)
    if not player:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Player not found."}},
        )
    return _player_to_out(player)
```

- [ ] **Step 4: Create `backend/app/api/analysis.py`**

```python
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.main import get_repo
from app.infrastructure.mongo_repository import MongoRepository
from app.config import settings

router = APIRouter()


class ScatterPoint(BaseModel):
    player_id: str
    name: str
    position: str
    xg_xa: float   # xG + xA
    g_a: float     # G + A


class ScatterDataOut(BaseModel):
    data: list[ScatterPoint]


@router.get("/analysis/scatter", response_model=ScatterDataOut)
def scatter_data(
    season: Optional[str] = None,
    repo: MongoRepository = Depends(get_repo),
) -> ScatterDataOut:
    resolved_season = season or settings.season
    raw = repo.get_scatter_data(resolved_season)
    points = []
    for doc in raw:
        agg = doc.get("aggregated_stats", {})
        points.append(ScatterPoint(
            player_id=doc.get("player_id", ""),
            name=doc.get("name", ""),
            position=doc.get("position", ""),
            xg_xa=float(agg.get("xg", 0)) + float(agg.get("xa", 0)),
            g_a=float(agg.get("goals", 0)) + float(agg.get("assists", 0)),
        ))
    return ScatterDataOut(data=points)
```

- [ ] **Step 5: Write API tests**

```python
# backend/tests/api/test_players.py
import mongomock
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app, get_repo, get_mode_factory
from app.infrastructure.mongo_repository import MongoRepository
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)


def _make_player(player_id: str = "1", season: str = "2025-2026") -> PlayerDTO:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = Score(offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06)
    return PlayerDTO(
        player_id=player_id, name="Test Player", season=season,
        position="FW", position_exact="ST", team="Arsenal",
        nationality="England", photo_url="https://example.com/p.jpg",
        competitions=[CompetitionEntry("England Premier League", stats, score)],
        aggregated_stats=stats,
        aggregated_scores=AggregatedScores(
            offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06,
            sleeper_ratio=1.3, sleeper_flag="HIGH_VALUE",
        ),
        low_sample_size=False,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def client() -> TestClient:
    mc = mongomock.MongoClient()
    repo = MongoRepository(mc)
    app.dependency_overrides[get_repo] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_player() -> TestClient:
    mc = mongomock.MongoClient()
    repo = MongoRepository(mc)
    repo.upsert_player(_make_player("1", "2025-2026"))
    app.dependency_overrides[get_repo] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_players_empty(client: TestClient) -> None:
    resp = client.get("/v1/players")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["data"] == []


def test_list_players_returns_player(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_player_found(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players/1")
    assert resp.status_code == 200
    assert resp.json()["player_id"] == "1"


def test_get_player_not_found(client: TestClient) -> None:
    resp = client.get("/v1/players/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 6: Run API tests**

```bash
cd backend && python -m pytest tests/api/test_players.py -v
```

Expected: All tests PASSED

- [ ] **Step 7: Run full test suite**

```bash
cd backend && python -m pytest -v
```

Expected: All tests PASSED

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/api/ backend/tests/api/
git commit -m "feat: add FastAPI app with all routers and API tests"
```

---

## Task 11: Frontend — App Shell and API Client

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/players.ts`
- Create: `frontend/src/api/fetch.ts`

- [ ] **Step 1: Create `frontend/src/api/client.ts`**

```typescript
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err?.detail?.message ?? err?.detail ?? 'API error')
  }
  return res.json() as Promise<T>
}
```

- [ ] **Step 2: Create `frontend/src/api/players.ts`**

```typescript
import { apiFetch } from './client'

export interface Stats {
  goals: number; assists: number; xg: number; xa: number
  minutes: number; clean_sheets: number; pk_saved: number; pk_won: number
  pk_scored: number; pk_taken: number; yellow_cards: number; red_cards: number
  fouls_committed: number; rating: number; big_chances_created: number; key_passes: number
}

export interface Score {
  offensive: number; defensive: number; tactical: number; s_final: number
}

export interface CompetitionEntry {
  competition: string; stats: Stats; scores: Score
}

export interface AggregatedScores extends Score {
  sleeper_ratio: number | null; sleeper_flag: 'HIGH_VALUE' | 'OVERPERFORMING' | null
}

export interface Player {
  player_id: string; name: string; season: string
  position: string; position_exact: string; team: string; nationality: string
  photo_url: string; competitions: CompetitionEntry[]
  aggregated_stats: Stats; aggregated_scores: AggregatedScores
  low_sample_size: boolean; last_updated: string
}

export interface PlayerList {
  data: Player[]; total: number; page: number; page_size: number
}

export interface ScatterPoint {
  player_id: string; name: string; position: string; xg_xa: number; g_a: number
}

export interface ScatterData { data: ScatterPoint[] }

export async function getPlayers(params: Record<string, string | number | undefined> = {}): Promise<PlayerList> {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString()
  return apiFetch<PlayerList>(`/v1/players${qs ? `?${qs}` : ''}`)
}

export async function getPlayer(playerId: string, season?: string): Promise<Player> {
  const qs = season ? `?season=${season}` : ''
  return apiFetch<Player>(`/v1/players/${playerId}${qs}`)
}

export async function getScatterData(season?: string): Promise<ScatterData> {
  const qs = season ? `?season=${season}` : ''
  return apiFetch<ScatterData>(`/v1/analysis/scatter${qs}`)
}
```

- [ ] **Step 3: Create `frontend/src/api/fetch.ts`**

```typescript
import { apiFetch } from './client'

export interface FetchRequest { season?: string; mode?: string }
export interface FetchResponse { status: string; season: string; mode: string }

export async function triggerFetch(req: FetchRequest = {}): Promise<FetchResponse> {
  return apiFetch<FetchResponse>('/v1/fetch/', {
    method: 'POST',
    body: JSON.stringify({ mode: 'fantasy', ...req }),
  })
}
```

- [ ] **Step 4: Create `frontend/src/App.tsx`**

```tsx
import { useState } from 'react'
import Rankings from './pages/Rankings'
import PlayerDetail from './pages/PlayerDetail'
import Compare from './pages/Compare'
import Sleepers from './pages/Sleepers'
import ScatterPage from './pages/ScatterPage'

type Tab = 'rankings' | 'detail' | 'compare' | 'sleepers' | 'scatter'

const TABS: { id: Tab; label: string }[] = [
  { id: 'rankings', label: 'Rankings' },
  { id: 'detail', label: 'Player Detail' },
  { id: 'compare', label: 'Compare' },
  { id: 'sleepers', label: 'Sleepers' },
  { id: 'scatter', label: 'Scatter Plot' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('rankings')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="bg-gray-900 border-b border-gray-800 px-4">
        <div className="flex gap-1 max-w-7xl mx-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      <main className="max-w-7xl mx-auto p-4">
        {tab === 'rankings' && <Rankings />}
        {tab === 'detail' && <PlayerDetail />}
        {tab === 'compare' && <Compare />}
        {tab === 'sleepers' && <Sleepers />}
        {tab === 'scatter' && <ScatterPage />}
      </main>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/api/ frontend/src/main.tsx frontend/src/index.css
git commit -m "feat: add frontend app shell and API client layer"
```

---

## Task 12: Frontend — Components

**Files:**
- Create: `frontend/src/components/FilterBar.tsx`
- Create: `frontend/src/components/PlayerTable.tsx`
- Create: `frontend/src/components/PlayerCard.tsx`
- Create: `frontend/src/components/ScatterPlot.tsx`

- [ ] **Step 1: Create `frontend/src/components/FilterBar.tsx`**

```tsx
interface Filters {
  position: string; team: string; nationality: string; sleeper_flag: string
}

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
}

const POSITIONS = ['', 'GK', 'DF', 'MF', 'FW']
const SLEEPER_FLAGS = ['', 'HIGH_VALUE', 'OVERPERFORMING']

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  const set = (key: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...filters, [key]: e.target.value })

  return (
    <div className="flex flex-wrap gap-3 mb-4">
      <select
        value={filters.position}
        onChange={set('position')}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
      >
        {POSITIONS.map((p) => <option key={p} value={p}>{p || 'All positions'}</option>)}
      </select>

      <input
        value={filters.team}
        onChange={set('team')}
        placeholder="Team..."
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-40"
      />

      <input
        value={filters.nationality}
        onChange={set('nationality')}
        placeholder="Nationality..."
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-40"
      />

      <select
        value={filters.sleeper_flag}
        onChange={set('sleeper_flag')}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
      >
        {SLEEPER_FLAGS.map((f) => <option key={f} value={f}>{f || 'All sleeper flags'}</option>)}
      </select>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/PlayerTable.tsx`**

```tsx
import type { Player } from '../api/players'

interface PlayerTableProps {
  players: Player[]
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onPlayerClick: (playerId: string) => void
}

export default function PlayerTable({
  players, total, page, pageSize, onPageChange, onPlayerClick,
}: PlayerTableProps) {
  const totalPages = Math.ceil(total / pageSize)

  const flagBadge = (flag: string | null) => {
    if (!flag) return null
    const color = flag === 'HIGH_VALUE' ? 'bg-green-800 text-green-200' : 'bg-amber-800 text-amber-200'
    return <span className={`text-xs px-2 py-0.5 rounded ${color}`}>{flag}</span>
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800 text-left">
              <th className="py-2 pr-4">#</th>
              <th className="py-2 pr-4">Player</th>
              <th className="py-2 pr-4">Pos</th>
              <th className="py-2 pr-4">Team</th>
              <th className="py-2 pr-4">S_final</th>
              <th className="py-2 pr-4">G</th>
              <th className="py-2 pr-4">A</th>
              <th className="py-2 pr-4">xG</th>
              <th className="py-2 pr-4">xA</th>
              <th className="py-2">Flag</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => (
              <tr
                key={p.player_id}
                onClick={() => onPlayerClick(p.player_id)}
                className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer"
              >
                <td className="py-2 pr-4 text-gray-500">{(page - 1) * pageSize + i + 1}</td>
                <td className="py-2 pr-4 font-medium">{p.name}</td>
                <td className="py-2 pr-4 text-gray-400">{p.position}</td>
                <td className="py-2 pr-4 text-gray-400">{p.team}</td>
                <td className="py-2 pr-4 font-mono text-indigo-300">{p.aggregated_scores.s_final.toFixed(2)}</td>
                <td className="py-2 pr-4">{p.aggregated_stats.goals}</td>
                <td className="py-2 pr-4">{p.aggregated_stats.assists}</td>
                <td className="py-2 pr-4 text-gray-400">{p.aggregated_stats.xg.toFixed(1)}</td>
                <td className="py-2 pr-4 text-gray-400">{p.aggregated_stats.xa.toFixed(1)}</td>
                <td className="py-2">{flagBadge(p.aggregated_scores.sleeper_flag)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex gap-2 mt-4 justify-center">
          <button
            disabled={page === 1}
            onClick={() => onPageChange(page - 1)}
            className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-gray-400">{page} / {totalPages}</span>
          <button
            disabled={page === totalPages}
            onClick={() => onPageChange(page + 1)}
            className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/PlayerCard.tsx`**

```tsx
import type { Player } from '../api/players'

interface PlayerCardProps { player: Player }

const StatRow = ({ label, value }: { label: string; value: string | number }) => (
  <div className="flex justify-between py-1 border-b border-gray-800 text-sm">
    <span className="text-gray-400">{label}</span>
    <span>{value}</span>
  </div>
)

export default function PlayerCard({ player: p }: PlayerCardProps) {
  const s = p.aggregated_stats
  const sc = p.aggregated_scores
  return (
    <div className="bg-gray-800 rounded-lg p-4 w-72">
      <div className="flex items-center gap-3 mb-4">
        {p.photo_url && (
          <img src={p.photo_url} alt={p.name} className="w-12 h-12 rounded-full object-cover bg-gray-700" />
        )}
        <div>
          <div className="font-semibold">{p.name}</div>
          <div className="text-xs text-gray-400">{p.position_exact} · {p.team}</div>
          <div className="text-xs text-gray-500">{p.nationality}</div>
        </div>
      </div>

      <div className="mb-3">
        <div className="text-xs text-gray-400 uppercase mb-1">Score</div>
        <div className="text-2xl font-mono text-indigo-300">{sc.s_final.toFixed(2)}</div>
        {sc.sleeper_flag && (
          <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${
            sc.sleeper_flag === 'HIGH_VALUE' ? 'bg-green-800 text-green-200' : 'bg-amber-800 text-amber-200'
          }`}>{sc.sleeper_flag}</span>
        )}
      </div>

      <StatRow label="Goals" value={s.goals} />
      <StatRow label="Assists" value={s.assists} />
      <StatRow label="xG" value={s.xg.toFixed(2)} />
      <StatRow label="xA" value={s.xa.toFixed(2)} />
      <StatRow label="Minutes" value={s.minutes} />
      <StatRow label="Rating" value={s.rating.toFixed(1)} />

      {p.competitions.length > 1 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 uppercase mb-1">Per Competition</div>
          {p.competitions.map((c) => (
            <div key={c.competition} className="text-xs py-1 flex justify-between">
              <span className="text-gray-400 truncate max-w-36">{c.competition}</span>
              <span className="font-mono text-indigo-300">{c.scores.s_final.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/components/ScatterPlot.tsx`**

```tsx
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import type { ScatterPoint } from '../api/players'

interface ScatterPlotProps { data: ScatterPoint[] }

const POSITION_COLORS: Record<string, string> = {
  GK: '#6366f1', DF: '#22c55e', MF: '#f59e0b', FW: '#ef4444',
}

export default function ScatterPlot({ data }: ScatterPlotProps) {
  const byPosition: Record<string, ScatterPoint[]> = {}
  for (const p of data) {
    const pos = p.position || 'MF'
    byPosition[pos] = byPosition[pos] ?? []
    byPosition[pos].push(p)
  }

  return (
    <ResponsiveContainer width="100%" height={500}>
      <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="g_a" name="G+A" type="number"
          label={{ value: 'Goals + Assists', position: 'insideBottom', offset: -10, fill: '#9ca3af' }}
          stroke="#6b7280"
        />
        <YAxis
          dataKey="xg_xa" name="xG+xA" type="number"
          label={{ value: 'xG + xA', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
          stroke="#6b7280"
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          content={({ payload }) => {
            if (!payload?.length) return null
            const p = payload[0].payload as ScatterPoint
            return (
              <div className="bg-gray-800 border border-gray-700 p-2 rounded text-sm">
                <div className="font-medium">{p.name}</div>
                <div className="text-gray-400">G+A: {p.g_a} · xG+xA: {p.xg_xa.toFixed(2)}</div>
              </div>
            )
          }}
        />
        <Legend />
        {Object.entries(byPosition).map(([pos, points]) => (
          <Scatter
            key={pos}
            name={pos}
            data={points}
            fill={POSITION_COLORS[pos] ?? '#9ca3af'}
            opacity={0.8}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add FilterBar, PlayerTable, PlayerCard, ScatterPlot components"
```

---

## Task 13: Frontend — Pages

**Files:**
- Create: `frontend/src/pages/Rankings.tsx`
- Create: `frontend/src/pages/PlayerDetail.tsx`
- Create: `frontend/src/pages/Compare.tsx`
- Create: `frontend/src/pages/Sleepers.tsx`
- Create: `frontend/src/pages/ScatterPage.tsx`

- [ ] **Step 1: Create `frontend/src/pages/Rankings.tsx`**

```tsx
import { useState, useEffect, useCallback } from 'react'
import { getPlayers, type Player, type PlayerList } from '../api/players'
import { triggerFetch } from '../api/fetch'
import FilterBar from '../components/FilterBar'
import PlayerTable from '../components/PlayerTable'

interface Filters { position: string; team: string; nationality: string; sleeper_flag: string }

export default function Rankings() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>({ position: '', team: '', nationality: '', sleeper_flag: '' })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [fetchMsg, setFetchMsg] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50 }
      if (filters.position) params.position = filters.position
      if (filters.team) params.team = filters.team
      if (filters.nationality) params.nationality = filters.nationality
      if (filters.sleeper_flag) params.sleeper_flag = filters.sleeper_flag
      setData(await getPlayers(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => { load() }, [load])

  const handleFetch = async () => {
    setFetchMsg('Scraping... this may take several minutes.')
    try {
      const r = await triggerFetch()
      setFetchMsg(`Done: ${r.season}`)
      load()
    } catch (e) {
      setFetchMsg(`Error: ${e instanceof Error ? e.message : 'Unknown'}`)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Player Rankings</h1>
        <div className="flex items-center gap-3">
          {fetchMsg && <span className="text-sm text-gray-400">{fetchMsg}</span>}
          <button
            onClick={handleFetch}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm font-medium"
          >
            Refresh Data
          </button>
        </div>
      </div>

      <FilterBar filters={filters} onChange={(f) => { setFilters(f); setPage(1) }} />

      {loading && <div className="text-gray-400 py-8 text-center">Loading...</div>}
      {data && !loading && (
        <PlayerTable
          players={data.data}
          total={data.total}
          page={page}
          pageSize={50}
          onPageChange={setPage}
          onPlayerClick={setSelectedId}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/pages/PlayerDetail.tsx`**

```tsx
import { useState } from 'react'
import { getPlayer, type Player } from '../api/players'
import PlayerCard from '../components/PlayerCard'

export default function PlayerDetail() {
  const [playerId, setPlayerId] = useState('')
  const [player, setPlayer] = useState<Player | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const search = async () => {
    if (!playerId.trim()) return
    setLoading(true)
    setError('')
    try {
      setPlayer(await getPlayer(playerId.trim()))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Not found')
      setPlayer(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Player Detail</h1>
      <div className="flex gap-2 mb-6">
        <input
          value={playerId}
          onChange={(e) => setPlayerId(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Player ID..."
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-60"
        />
        <button
          onClick={search}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm"
        >
          Search
        </button>
      </div>
      {loading && <div className="text-gray-400">Loading...</div>}
      {error && <div className="text-red-400">{error}</div>}
      {player && <PlayerCard player={player} />}
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/pages/Compare.tsx`**

```tsx
import { useState } from 'react'
import { getPlayer, type Player } from '../api/players'
import PlayerCard from '../components/PlayerCard'

export default function Compare() {
  const [input, setInput] = useState('')
  const [players, setPlayers] = useState<Player[]>([])
  const [error, setError] = useState('')

  const add = async () => {
    if (!input.trim() || players.length >= 5) return
    try {
      const p = await getPlayer(input.trim())
      if (!players.find((x) => x.player_id === p.player_id)) {
        setPlayers([...players, p])
      }
      setInput('')
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Not found')
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Compare Players</h1>
      <div className="flex gap-2 mb-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder="Player ID..."
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-60"
          disabled={players.length >= 5}
        />
        <button
          onClick={add}
          disabled={players.length >= 5}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm disabled:opacity-40"
        >
          Add
        </button>
        {players.length > 0 && (
          <button
            onClick={() => setPlayers([])}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
          >
            Clear
          </button>
        )}
      </div>
      {error && <div className="text-red-400 mb-3">{error}</div>}
      <div className="flex flex-wrap gap-4">
        {players.map((p) => <PlayerCard key={p.player_id} player={p} />)}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/pages/Sleepers.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { getPlayers, type PlayerList } from '../api/players'
import PlayerTable from '../components/PlayerTable'

export default function Sleepers() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [flag, setFlag] = useState<'HIGH_VALUE' | 'OVERPERFORMING'>('HIGH_VALUE')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getPlayers({ sleeper_flag: flag, page, page_size: 50 })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [flag, page])

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Sleeper Picks</h1>
      <div className="flex gap-2 mb-4">
        {(['HIGH_VALUE', 'OVERPERFORMING'] as const).map((f) => (
          <button
            key={f}
            onClick={() => { setFlag(f); setPage(1) }}
            className={`px-4 py-2 rounded text-sm ${
              flag === f ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {f === 'HIGH_VALUE' ? 'High Value Sleepers' : 'Overperforming'}
          </button>
        ))}
      </div>
      {loading && <div className="text-gray-400 py-8 text-center">Loading...</div>}
      {data && !loading && (
        <PlayerTable
          players={data.data}
          total={data.total}
          page={page}
          pageSize={50}
          onPageChange={setPage}
          onPlayerClick={() => {}}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create `frontend/src/pages/ScatterPage.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { getScatterData, type ScatterPoint } from '../api/players'
import ScatterPlot from '../components/ScatterPlot'

export default function ScatterPage() {
  const [data, setData] = useState<ScatterPoint[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getScatterData()
      .then((r) => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">xG+xA vs G+A</h1>
      <p className="text-gray-400 text-sm mb-4">
        Points above the diagonal are underperformers (high xG, low output) — potential sleepers.
      </p>
      {loading && <div className="text-gray-400 py-8 text-center">Loading...</div>}
      {!loading && <ScatterPlot data={data} />}
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: add all frontend pages (Rankings, PlayerDetail, Compare, Sleepers, ScatterPage)"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - POST /v1/fetch/ → `api/fetch.py` Task 10
  - GET /v1/players with all filters → `api/players.py` Task 10
  - GET /v1/players/{id} → `api/players.py` Task 10
  - GET /v1/analysis/scatter → `api/analysis.py` Task 10
  - ScoringEngine formula → Task 3 (verified against Mathematical_Specification.md)
  - SleeperDetector logic → Task 4
  - MongoRepository indexes → Task 6 (compound + season + s_final)
  - Dual source (Sofascore + FBref) merge → Tasks 7, 8, 9
  - Tor proxy → Task 1 docker-compose.yml (ALL_PROXY=socks5://tor:9050)
  - ModeFactory + AnalysisMode ABC → Task 9
  - competitions.yaml → Task 5
  - All 5 frontend pages → Task 13
  - All 4 frontend components → Task 12
  - PlayerDTO with player_id, name, team, nationality, photo_url, competitions, aggregated → Task 2
  - Low sample size flag (minutes < 90) → FantasyMode in Task 9
  - Docker Compose 4 services → Task 1

- [x] **No placeholders** — all code is complete in each step

- [x] **Type consistency** — `Stats`, `Score`, `CompetitionEntry`, `PlayerDTO`, `AggregatedScores` defined in Task 2 and used consistently through Tasks 3-13
