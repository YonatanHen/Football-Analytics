# Mathematical Specification: Position-Adjusted Selection Index ($S_{final}$)

This document defines the logic for the AI selection engine. Use these formulas to calculate the player performance index based on historical stats and predictive metrics (xG/xA).

---

## 1. The Master Equation

$$S_{final} = \min\!\left(10,\ \max\!\left(0,\ 10 \times \frac{R}{E}\right)\right), \qquad E = 8.0$$

$$R = \frac{Offensive + Defensive + Tactical}{\max(Minutes / 90,\ 1)} \times B_{starter} \times C_{apps} + B_{time}$$

Where:

$$B_{starter} = 1 + 0.2 \times \min\!\left(1,\ \frac{MatchesStarted}{Appearances}\right)$$

$$C_{apps} = \begin{cases} 0.15 & \text{if } Appearances < 5 \\ 0.50 & \text{if } 5 \leq Appearances < 15 \\ 0.80 & \text{if } 15 \leq Appearances < 20 \\ 1.00 & \text{if } Appearances \geq 20 \end{cases}$$

$$B_{time} = 0.5 \times \frac{\min(avg,\ 59)}{59} + 0.5 \times \frac{\max(0,\ \min(avg,\ 90) - 59)}{31}, \qquad avg = \frac{Minutes}{Appearances}$$

- $C_{apps}$: appearance-based confidence multiplier. Dampens inflated per-90 rates for low-game-count players; reaches full weight at 20+ appearances. Team-specific match tracking is a planned improvement. Exposed via the API as `aggregated_scores.confidence`, computed at request time by `confidence_tier()`/`effective_appearances()` in `scoring_engine.py` — it is not stored in MongoDB.
- $S_{final}$ is always in $[0, 10]$ and depends only on the player's own stats. $E$ (`ELITE_RAW`) is a fixed constant: a raw score of 8 maps to 10. It is never derived from the data.
- The per-90 denominator has a floor of one full match, $\max(Minutes/90, 1)$. So a single card in a few minutes cannot produce an extreme negative rate.
- $B_{time}$ is in $[0, 1]$. It uses average minutes per appearance: 0.5 for the first 59 minutes, 0.5 for minutes 60-90. It does not grow with total minutes, so loading another competition does not raise it.
- If $Minutes = 0$, $S_{final} = 0$. The three pillars are still computed.
- If $Appearances \leq 0$ but $Minutes > 0$ (legacy, corrupt, or partially scraped records), $Appearances$ is estimated as $\lceil Minutes / 90 \rceil$ so the record still ranks instead of silently scoring 0. Ceiling, not rounding: rounding can imply more than 90 minutes per appearance (1300 minutes rounds to 14, i.e. 92.9 min each), which the $\min(avg,90)$ split would then silently truncate. The $\min$ in $B_{starter}$ bounds it to $[1.0, 1.2]$ even when $MatchesStarted$ exceeds the estimate.
- An estimated count assumes full 90-minute appearances, so it yields the maximum $B_{time}$ (1.0). A record with missing appearance data can therefore out-score an otherwise identical record that shows real rotation.

---

## 2. Pillar Calculations

### A. Offensive Score

$$Offensive = (G \times w_G) + (A \times w_A) + xG + xA$$

| Position | Goal Weight ($w_G$) | Assist Weight ($w_A$) |
| :--- | :---: | :---: |
| **GK** (Goalkeeper) | 10 | 5 |
| **DF** (Defender) | 6 | 4 |
| **MF** (Midfielder) | 5 | 3 |
| **FW** (Forward) | 4 | 3 |

### B. Defensive Score

* **Goalkeepers (GK):**
    $$Defensive_{GK} = (CS \times 5) + (PK_{saved} \times 5) + (GoalsPrevented \times 2)$$

    $GoalsPrevented = xGoals_{faced} - GoalsConceded$ (positive = outperformed expectations).

* **Defenders (DF):**
    $$Defensive_{DF} = CS \times 4$$

* **Midfielders & Forwards (MF/FW):**
    $$Defensive_{MF/FW} = 0$$

### C. Tactical & Discipline Score

$$Tactical = (PK_{won} \times 2) + \left(\frac{PK_{scored}}{PK_{taken}} \times 5\right) - Y - (YR \times 2) - (DR \times 4) - (F_c \times 0.2)$$

| Variable | Description | Value |
| :--- | :--- | :--- |
| $PK_{won}$ | Penalties won (fouled in the box) | +2 pts |
| $PK_{ratio}$ | Penalty success rate (Scored / Taken) | $\times 5$ weight |
| $Y$ | Yellow Cards | −1 pt |
| $YR$ | 2nd Yellow → Red Cards | −2 pts |
| $DR$ | Direct Red Cards (straight red) | −4 pts |
| $F_c$ | Fouls Committed | −0.2 pts per foul |

Note: `red_cards` (total reds) is stored for display only and is **not** used in scoring. Scoring uses the split `yellow_red_cards` and `direct_red_cards` fields.

---

## 3. Advanced Analysis (The Sleeper Finder)

To identify undervalued players the AI calculates the **Sleeper Ratio**:

$$Sleeper Ratio = \frac{xG + xA}{G + A}$$

**Logic Gate:**
- If $Ratio > 1.2$ AND $Minutes > 450$: Flag as **High Value Sleeper**.
- If $Ratio < 0.8$: Flag as **Overperforming** (conversion may drop off).

---

## 4. Data Constraints for Python Implementation

- **Null Handling**: All missing values for $xG$, $xA$, or $PK$ stats must be treated as `0`.
- **Position Mapping**: Position strings (e.g., `CB`, `LB`, `RB`) are mapped to the generic `DF` category to apply the correct weights.
- **Low Sample Size**: If aggregated $Minutes < 90$, the player is flagged `low_sample_size = true`.
- **League Context**: `total_matches` per `(competition, season)` is stored in the `league_meta` MongoDB collection and set on each `CompetitionEntry` at fetch time.
