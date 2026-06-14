# Mathematical Specification: Position-Adjusted Selection Index ($S_{pos}$)

This document defines the logic for the AI selection engine. Use these formulas to calculate the player performance index based on historical stats and predictive metrics (xG/xA).

---

## 1. The Master Equation
The final score for every player is the sum of three distinct performance pillars, normalized by their time on the pitch.

$$S_{final} = \frac{Offensive + Defensive + Tactical}{Minutes / 90}$$

---

## 2. Pillar Calculations

### A. Offensive Score
Calculates the value of direct contributions. Goals and Assists are weighted by position to reflect rarity. **xG** and **xA** are added as raw values to account for underlying quality.

$$Offensive = (G \times w_G) + (A \times w_A) + xG + xA$$

| Position | Goal Weight ($w_G$) | Assist Weight ($w_A$) |
| :--- | :---: | :---: |
| **GK** (Goalkeeper) | 10 | 5 |
| **DF** (Defender) | 6 | 4 |
| **MF** (Midfielder) | 5 | 3 |
| **FW** (Forward) | 4 | 3 |

### B. Defensive Score
Clean sheets ($CS$) are only calculated for defensive positions. Goalkeepers for shot-stopping and penalty saves.

* **Goalkeepers (GK):**
    $$Defensive_{GK} = (CS \times 5) + (PK_{saved} \times 5) 
* **Defenders (DF):**
    $$Defensive_{DF} = CS \times 4$$
* **Midfielders & Forwards (MF/FW):**
    $$Defensive_{MF/FW} = 0$$

### C. Tactical & Discipline Score
This component rewards set-piece reliability and penalizes poor discipline or high-risk play styles.

$$Tactical = (PK_{won} \times 2) + (\frac{PK_{scored}}{PK_{taken}} \times 5) - Y - (R \times 3) - (F_c \times 0.2)$$

| Variable | Description | Value |
| :--- | :--- | :--- |
| $PK_{won}$ | Penalties "squeezed" (fouled in the box) | +2 pts |
| $PK_{ratio}$ | Penalty success rate (Scored / Taken) | $\times 5$ weight |
| $Y$ | Yellow Cards | -1 pt |
| $R$ | Red Cards | -3 pts |
| $F_c$ | Fouls Committed | -0.2 pts per foul |

---

## 3. Advanced Analysis (The Sleeper Finder)

To identify players who are currently undervalued by traditional fantasy points, the AI calculates the **Sleeper Ratio**. This identifies players whose creative/offensive input is high, but whose conversion (luck) has been low.

$$Sleeper Ratio = \frac{xG + xA}{G + A}$$

**Logic Gate:**
- If $Ratio > 1.2$ AND $Minutes > 450$: Flag as **High Value Sleeper**.
- If $Ratio < 0.8$: Flag as **Overperforming** (Potential for points to drop off).

---

## 4. Data Constraints for Python Implementation
- **Null Handling**: All missing values for $xG$, $xA$, or $PK$ stats must be treated as `0`.
- **Position Mapping**: Ensure position strings (e.g., 'CB', 'LB', 'RB') are mapped to the generic 'DF' category to apply the correct weights.
- **Normalization**: If $Minutes < 90$, the $S_{final}$ should be flagged as "Low Sample Size" to avoid skewing the rankings with bench-warmers.