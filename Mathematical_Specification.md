# Mathematical Specification: Position-Adjusted Selection Index ($S_{final}$)

This document defines the logic for the AI selection engine. Use these formulas to calculate the player performance index based on historical stats and predictive metrics (xG/xA).

---

## 1. The Master Equation

$$S_{final} = \frac{Offensive + Defensive + Tactical}{Minutes / 90} \times F_{time} \times B_{starter}$$

Where:

$$F_{time} = \min\!\left(1,\ \frac{Minutes}{\sum_{c}\ TotalMatches_c \times 90}\right)$$

$$B_{starter} = 1 + 0.2 \times \frac{MatchesStarted}{Appearances} \quad (\text{1.0 if } Appearances = 0)$$

- $\sum_{c} TotalMatches_c$ is the sum of matches played in each competition the player appeared in (sourced from `league_meta`). This makes the factor season-aware: a player who played 1 of 20 available matches scores far lower than one who played 1 of 1.
- If $\sum_{c} TotalMatches_c = 0$ (legacy data), $F_{time} = 1.0$.
- If $Minutes = 0$, $S_{final} = 0$.

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
