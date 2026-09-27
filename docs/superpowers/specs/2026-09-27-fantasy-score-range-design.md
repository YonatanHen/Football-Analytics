# Fantasy Score in a strict 0-10 range — design

- **Date:** 2026-09-27
- **Branch:** `dev/fantasy-score-range` (stacked on `dev/chat-model-fallback`)
- **Status:** approved; implemented, with the follow-up in section 8

## 1. Goal

The Fantasy Score (`s_final`) must always be between 0 and 10.

What the user asked for:

- A player's score depends **only on that player's own performance**. It is not a rank or a percentile, and it does not use the best, worst or percentile values of other players.
- Two or more players can have the same score.
- All players are on the same 0-10 scale, so scores can be compared.
- When a competition is loaded, the players in that competition get new scores from their own updated stats. Players in other competitions do not change.

## 2. The problem today

Measured on the 1649 players in the DB (2025-2026) with the current formula:

| | Value |
|---|---|
| Minimum | −13.50 (Samuel Nibombe: 1 minute, 1 yellow card) |
| Median | 1.52 |
| Maximum | 12.09 (Harry Kane) |
| Below 0 | 121 players |
| Above 10 | 1 player |

There are two causes:

1. **Tiny minutes.** `raw_per90` divides points by `minutes / 90`. For 1 minute that is ÷ 0.011, so one yellow card (−1) becomes −90 per 90 minutes. The confidence tier (0.15) reduces this only to −13.5.
2. **The playing-time bonus has no limit.** It pays 0.001 to 0.0015 per minute for **all** minutes of the season. Kane gets +3.83 for 3421 minutes. More competitions give more minutes, so loading a competition raises the bonus.

There is also a data problem. The per-competition scores (`competitions[].scores`) were never rescored after the last formula change, and `rescore_players.py` rescores only the combined score. As a result, 1120 of the 1649 stored combined scores differ from the current formula.

## 3. Rejected approaches

- **Percentile rank:** the score would say how many players you beat. Rejected because the user wants individual performance only.
- **Min-max / clipped min-max over the player pool:** the score would depend on the pool's extremes or percentiles. Loading a league would then change every player's score. Rejected for the same reason.
- **Smooth curve `10 × (1 − e^(−raw/4))`:** it squeezes the top. Kane and Olise are 2.27 apart in raw score but only 0.79 apart after the curve.
- **Hard limit only `clamp(raw, 0, 10)`:** most of the scale stays unused. The median player gets 1.14.

## 4. Design

### 4.1 Formula (`backend/app/domain/scoring_engine.py`)

```
per90         = (offensive + defensive + tactical) / max(minutes / 90, 1)
starter_bonus = 1 + 0.2 × min(1, matches_started / apps)            (unchanged)
confidence    = tier(apps): <5 → 0.15, 5-14 → 0.50, 15-19 → 0.80, 20+ → 1.00  (unchanged)
avg           = minutes / apps
bonus         = 0.5 × min(avg, 59) / 59  +  0.5 × max(0, min(avg, 90) − 59) / 31
raw           = per90 × starter_bonus × confidence + bonus
s_final       = clamp(10 × raw / ELITE_RAW, 0, 10),   ELITE_RAW = 8.0
```

- **Fix 1: minutes floor.** Every player counts as having played at least one full match (90 minutes) in the per-90 part. One card in 1 minute is −1 per 90, not −90 per 90.
- **Fix 2: bonus based on average minutes.** The bonus depends on average minutes per appearance, with a maximum of 1.0. It still rewards the late minutes (60-90) as much as the early ones: each part is worth 0.5. The number of appearances is already rewarded by `confidence`, so the bonus no longer grows with total minutes.
- **Option C: fixed scale.** A raw score of `ELITE_RAW` (8.0) maps to 10, on a straight line. The result is clamped to [0, 10]. `ELITE_RAW` is a fixed constant in the code and in the spec. It is never taken from the data.
- `apps` is `effective_appearances(stats)`, unchanged. A player with 0 minutes keeps `s_final = 0`.
- `offensive`, `defensive` and `tactical` do not change. They are not limited to 0-10, because they are raw point sums.

### 4.2 Expected result (current DB, with this design)

| Player | Raw | Score |
|---|---|---|
| Harry Kane | 9.06 | 10.00 |
| Michael Olise | 6.79 | 8.49 |
| Erling Haaland | 6.59 | 8.24 |
| Luis Díaz | 6.23 | 7.79 |
| Matheus Cunha (top 10%) | 2.93 | 3.66 |
| Daniel Bragança (median) | 1.14 | 1.42 |
| Kevin Akpoguma | −2.09 | 0.00 |

Across the pool: 1 player at 10, 65 at 0, median 1.42.

### 4.3 Where it applies

Every score is computed by `ScoringEngine.calculate()`, so the range applies everywhere and no caller changes:

- combined score at fetch time and in `build_player()` (`player_assembler.py`)
- per-competition score at fetch time (`fetch_runner.py`)
- competition view re-aggregation (`mongo_repository._apply_stats_view`)
- the chat agent's per-competition Fantasy Score (`agent/tools/base.competition_value`)

### 4.4 Stored data

- **New loads** (via `tools/fetch_cli`) store 0-10 scores directly.
- **Existing data:** extend the rescore script (now `backend/scripts/DB/rescore_players.py`, covering every season) so it rescores **each competition entry** (`competitions[].scores`) and then the combined score. Run it once after the change:
  1. Take a DB snapshot (`scripts/DB/snapshot_dump.py`).
  2. Run the rescore, only after the user approves.
  3. Check: all stored `s_final` values are within [0, 10], and the stored values match the formula.

### 4.5 Unaffected

- Frontend: it only shows the backend value (`toFixed(2)`). The table score bar scales to the page maximum. No change is needed.
- Sleeper / xGI Outliers: they use xG, xA, goals and assists, not `s_final`.
- API shape: same fields, only new values.

### 4.6 Chat agent

The system prompt mentions that the Fantasy Score is on a 0-10 scale, so the model can describe it correctly.

## 5. Testing

Backend unit tests (`backend/tests/domain/test_scoring_engine.py`):

- The minutes floor: 1 yellow card in 1 minute gives a score of 0, not a large negative number.
- The bonus is at most 1.0. A 90-minute average gives exactly 1.0, and a 59-minute average gives 0.5.
- The clamp: a very strong season gives exactly 10, and a net-negative season gives exactly 0.
- Linear in between: a known raw value of 4.0 gives 5.0.
- Property test: for many random `Stats` and every position, `0 ≤ s_final ≤ 10`.
- Independence: the same stats give the same score. Loading more minutes in a new competition does not raise the bonus beyond 1.0.
- Update existing tests that expect values from the old formula.

Rescore script test: per-competition scores are recomputed, not only the combined score.

Validation: the data-analyst agent checks `ELITE_RAW = 8.0` and the two fixes against the real distribution per position (GK/DF/MF/FW) before the change is finalized. If a position is clearly favored, that goes back to the user as a decision. It is not tuned silently.

## 6. Documentation

- `Mathematical_Specification.md`: the new master equation, fixes 1 and 2, and the 0-10 scale with `ELITE_RAW`.
- `CLAUDE.md` "Key domain concepts": the `s_final` formula line.
- `README.md`: the Fantasy Score description, if it mentions the range or formula.

## 7. Out of scope

- Changing the pillar weights (goals, assists, clean sheets, cards).
- Changing the confidence tiers or the starter bonus.
- Any frontend change.

## 8. Follow-up after data validation (approved 2026-09-27)

The data-analyst check found that few-minute players still reached the top, for example Waldschmidt at #5 with 684 minutes. The user approved two changes. They replace "confidence tiers unchanged" in section 4.1:

- **A. Confidence counts minutes.** `confidence = min(tier(appearances), tier(minutes // 60))`, with the same tiers (`<5` → 0.15, `5-14` → 0.50, `15-19` → 0.80, `20+` → 1.00).
  - Dividing by 60, not 90, keeps regular starters who are subbed off around the 60th minute at full confidence. With ÷ 90, their median would drop from 2.28 to 2.03.
  - The API's `aggregated_scores.confidence` uses the same function (`score_confidence()`).
- **B. The bonus is scaled by confidence.** `raw = (per90 × starter_bonus + bonus) × confidence`. One quiet full match now gives 0.19, not 1.25.

Measured effect: the top 20 has no player under 900 minutes (it had 3). Waldschmidt goes from 7.50 to 3.75, and Pepi (154 minutes) from 6.51 to 1.95. Kane, Olise, Raya and Rice do not change.

**Position balance (C): no change, by design.** Defenders and goalkeepers score mainly from clean sheets, plus goals and assists. Goalkeepers also score from penalties saved. Forwards being more common at the top is accepted.

**Open:** defensive midfielders get no defensive credit (D). This needs its own design.
