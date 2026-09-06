# Defender Representation — Design Spec

**Date:** 2026-07-11
**Status:** Layer 1 implemented 2026-09-06 on `dev/defender-metrics`. Layer 2 is obsolete.
Layer 3 is still an open proposal.
**Branch:** `dev/defender-metrics`

## Status update — 2026-09-06

**Layer 1 is done.** Thirteen defensive fields are typed on `Stats`, populated from
`raw_stats` on both the live-fetch path and a one-off backfill, aggregated as counts with
the two rates recomputed from the summed counts. They are in `METRIC_FIELDS`, so they are
sortable and filterable, exposed by `StatsOut`, and mirrored in the frontend `Stats` and
`METRIC_OPTIONS`. The backfill updated 1235 of 1256 `player_stats` docs across 1394
competition entries; no re-fetch was needed, exactly as this spec predicted.

**Field set — question 1 answered by trimming.** Shipped: `tackles`, `tackles_won`,
`interceptions`, `clearances`, `blocks`, `aerial_duels_won`, `aerial_lost`,
`ball_recoveries`, `dribbled_past`, `errors_lead_to_goal`, `errors_lead_to_shot`, plus
the rates `tackles_won_pct` and `aerial_duels_won_pct`. Dropped for now: `duels_won_pct`
(overlaps the aerial rate) and `pass_accuracy_pct` (a ball-playing metric, not a
defending one). Both remain available in `raw_stats` if wanted later.

**Layer 2 is obsolete.** It targeted the RAG document builder
(`backend/app/domain/player_document.py`) for embedding quality. RAG was cancelled and
that module no longer exists. The consumer of Layer 1 is now the Rankings filters and the
chatbot agent's `defending` tool, which read `METRIC_FIELDS` directly — no prose needed.

**Layer 3 is unchanged and still needs sign-off.** Scoring was deliberately left out:
`ScoringEngine` does not read these fields, so `s_final` is untouched and no
`Mathematical_Specification.md` update is required by this change. Questions 3 and 4
below are still open.

## Problem

Defenders are currently evaluated and described through an **attacking lens**. Both
the RAG document builder (`playground/document_builder.py` → `backend/app/domain/player_document.py`)
and the `s_final` scoring see only the typed `Stats` model, which is an attacking +
goalkeeping schema. Its only defensive signal is `clean_sheets` (a team-level proxy)
and `fouls_committed`.

Concretely, `_outfield_headline()` picks a defender's adjective from *finishing* and
*creativity* traits only; when neither fires it emits the static string
`"defensively solid"` with **no data behind it**. Result: semantic retrieval for
queries like *"solid defender"* ranks players on attacking prose, and star defenders
(whose docs emphasise their goals/assists) are mis-ranked.

## Data availability — the metrics already exist

Every defensive stat we want is **already scraped and stored** in each competition
entry's untyped `raw_stats` blob; we simply never promote it into the typed model.
Verified present on real player docs:

| Concept | `raw_stats` key |
|---|---|
| Tackles / won / win % | `tackles`, `tacklesWon`, `tacklesWonPercentage` |
| Interceptions | `interceptions` |
| Clearances | `clearances` |
| Blocks | `outfielderBlocks`, `blockedShots` |
| Aerial duels won / win % | `aerialDuelsWon`, `aerialDuelsWonPercentage`, `aerialLost` |
| Ground/total duels win % | `groundDuelsWonPercentage`, `totalDuelsWonPercentage` |
| Ball recoveries | `ballRecovery` |
| Dribbled past (negative) | `dribbledPast` |
| Errors (negative) | `errorLeadToGoal`, `errorLeadToShot` |
| Passing quality (ball-players) | `accuratePassesPercentage`, `accurateLongBallsPercentage` |

No new scraping is required.

## Layer 1 — Promote defensive fields into `Stats`

Add these fields to `Stats` in `backend/app/domain/models.py` and populate them in
`player_assembler` from `raw_stats` (defaulting to 0 when absent — GK/older rows):

- Counts: `tackles`, `tackles_won`, `interceptions`, `clearances`, `blocks`
  (`outfielderBlocks`), `aerial_duels_won`, `aerial_lost`, `ball_recoveries`,
  `dribbled_past`, `errors_lead_to_goal`, `errors_lead_to_shot`
- Percentages: `tackles_won_pct`, `aerial_duels_won_pct`, `duels_won_pct`
  (`totalDuelsWonPercentage`), `pass_accuracy_pct`

**Aggregation rule (important):** percentages must be **recomputed from summed
counts** across competitions (e.g. `tackles_won_pct = Σtackles_won / Σtackles`), NOT
averaged — averaging percentages across competitions with different volumes is wrong.
Where a raw count for the denominator is unavailable, keep the season percentage as-is
and document the limitation.

Mirror the new fields into `StatsOut` (API) and `Stats` (frontend `players.ts`) and add
the useful ones to `METRIC_OPTIONS` / `METRIC_FIELDS` so they become sortable/filterable
(this also makes them answerable on the structured RAG path — e.g. "best tacklers").

## Layer 2 — Defender-aware document (OBSOLETE — RAG cancelled)

Add `_defender_headline(player)` and a defender branch in the summary. Priority order
matches the analyst's mental model: **clean sheets → tackle success → aerial dominance
→ interceptions/clearances → then goals/assists.**

**Clean sheets — a representation gap, not a data gap.** `clean_sheets` is already
captured (Sofascore `cleanSheet` → typed `Stats`, aggregated, and scored `×4` for DF),
but the document builder currently mentions it **only in the per-competition stat line** —
the outfield *summary prose* and the *aggregated per-90 block* omit it entirely. So the
embedding barely sees it. Surfacing it is part of this layer: clean sheets must appear in
the defender **headline** and in the aggregated defensive line, not just per-competition.

Proposed headline adjective (first match wins):
- `"commanding"` — high `aerial_duels_won_pct` (≥ 60%) with meaningful clean sheets
- `"combative ball-winner"` — high `tackles_won_pct` (≥ 65%) and interceptions per 90
- `"ball-playing"` — high `pass_accuracy_pct` (≥ 88%) / accurate long balls
- `"dependable"` — otherwise (replaces the empty `"defensively solid"`)

Add a **defensive stat line** to the outfield document (populated for all outfielders,
but it is the *lead* for DF):
```
Defensive: 2.3 tackles/90 (71% won), 1.8 interceptions/90, 3.1 clearances/90,
           68% aerial duels won, 0.4 blocks/90, 0 errors leading to a goal.
```
Attacking output stays, but for DF it moves **after** the defensive line.

## Layer 3 — Scoring (PROPOSAL — still needs sign-off, not implemented)

Optional; only if we choose "docs + scoring". Fold defensive output into `s_final` for
`position == "DF"` (and partially MF). This changes app-wide ranking and requires a
`Mathematical_Specification.md` update. **All weights below are placeholders for review,
not final:**

| Metric (per 90) | Proposed weight |
|---|---|
| Tackle won | +0.6 |
| Interception | +0.6 |
| Clearance | +0.2 |
| Block | +0.5 |
| Aerial duel won | +0.4 |
| Ball recovery | +0.1 |
| `errorLeadToGoal` | −3.0 |
| `errorLeadToShot` | −1.0 |
| Dribbled past | −0.3 |

Quality percentages (`tackles_won_pct`, `aerial_duels_won_pct`) act as **multipliers**
on the corresponding volume term rather than standalone additive points, so high-volume
low-quality defenders aren't overrated. Normalisation and `playing_time_factor` /
`starter_bonus` stay as in the current `s_final`.

## Out of scope

- No new scraping or data sources.
- No change to GK scoring/representation.
- No re-fetch required — a one-off backfill re-reads existing `raw_stats` into the new
  typed fields (a small migration script over `player_stats`).

## Open questions for review

1. Field set — is the Layer-1 list right, or trim/extend (e.g. drop `duels_won_pct`)?
2. Headline thresholds (60% aerial, 65% tackle, 88% pass) — reasonable, or tune?
3. Scoring: in scope now, or docs+retrieval only and defer scoring to a follow-up?
4. If scoring is in scope, do the proposed weights need a data-distribution check first
   (data-analyst) before we commit numbers to the math spec?
