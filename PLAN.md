# Blueprint: AI Fantasy Football Selection Engine (v2.0)

This document provides a structured roadmap for building a player selection tool using **ScraperFC** to pull high-fidelity data from FBref/Understat.

---

## 1. Project Overview
- **Goal**: Rank fantasy players using a Position-Adjusted Selection Index ($S_{pos}$).
- **Input**: ScraperFC (Primary) | Screenshot OCR (Fallback).
- **Metric Logic**: xG and xA are included as raw values; positional rarity is weighted.
- **Target**: Identify high-value starters and "Sleeper" picks.

---

## 2. Updated Scoring Formula ($S_{pos}$)

| Metric | GK | DF | MF | FW |
| :--- | :---: | :---: | :---: | :---: |
| **Goal (G)** | 10 | 6 | 5 | 4 |
| **Assist (A)** | 5 | 4 | 3 | 3 |
| **Clean Sheet (CS)**| 5 | 4 | 0 | 0 |
| **xG / xA** | 1.0 | 1.0 | 1.0 | 1.0 |

**Formula Constraints:**
- **Goalkeepers**: +5 per Penalty Saved, +1 per 3 saves.
- **Set Pieces**: (Penalty Scored / Penalty Taken) × 5.
- **Impact**: +2 for Penalties Won (Squeezed).
- **Discipline**: Yellow (-1), Red (-3), Fouls Committed (-0.2).
- **Normalization**: All final scores are $\text{Score} / (\text{Minutes Played} / 90)$.

---

## 3. Phase-by-Phase Claude Prompts

### Phase 1: The ScraperFC Data Pipeline
**Prompt to Claude:**
> "Write a Python script using the `ScraperFC` library to fetch player statistics from FBref for the [INSERT LEAGUE, e.g., 'EPL'] 2025-2026 season.
> 1. Use the `FBref` module to scrape 'Standard Stats' (for goals, assists, xG, xA) and 'Playing Time'.
> 2. Use the 'Miscellaneous' stats to get yellow/red cards, fouls committed, and penalties won.
> 3. Merge these into a single Pandas DataFrame keyed by Player Name.
> 4. Ensure all numeric columns are cast correctly and handle 'NaN' by filling with 0."

### Phase 2: The Logic Engine (DataFrames)
**Prompt to Claude:**
> "Create a Python function `apply_selection_logic(df)` that processes a ScraperFC DataFrame.
> 
> Implement these specific weights:
> - Goals: GK:10, DF:6, MF:5, FW:4 | Assists: GK:5, DF:4, MF:3, FW:3.
> - Clean Sheets: GK:5, DF:4 (Skip MF/FW).
> - xG and xA: Add raw values directly to the score (weight=1.0).
> - Penalties: Add 2 pts for penalties won. Calculate penalty success rate (scored/taken) and multiply by 5. For GKs, add 5 pts per penalty saved.
> - Discipline: Deduct 1 for Yellow, 3 for Red, and 0.2 per foul committed.
> - Final step: Normalize the score to a 'Per 90' metric: `total_score / (minutes / 90)`."

### Phase 3: The Optimizer & Sleeper Finder
**Prompt to Claude:**
> "Analyze the resulting scored DataFrame:
> 1. Rank the top 5 'Best Value' players per position.
> 2. Create a 'Sleeper' list: Find players whose (xG + xA) > (Actual Goals + Actual Assists) by a margin of 20% or more.
> 3. Generate a brief report for the top 3 sleepers explaining that their underlying performance suggests a high probability of upcoming points."

### Phase 4: Streamlit UI
**Prompt to Claude:**
> "Build a Streamlit dashboard that:
> 1. Connects to the ScraperFC script to refresh data.
> 2. Displays a searchable table of all players and their calculated S-Score.
> 3. Visualizes 'Expected vs. Actual' performance using a Plotly scatter plot (xG+xA on one axis, Goals+Assists on the other)."

---

## 4. Technical Strategy for ScraperFC
Since ScraperFC can sometimes be slow due to FBref's rate limits, instruct Claude to implement a **caching layer**:
- `df.to_parquet('stats_cache.parquet')` 
- This allows you to tweak your scoring formula in the UI (Phase 4) without re-scraping the web every time you hit 'Run'.