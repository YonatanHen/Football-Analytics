class SleeperDetector:
    def classify(self, xg: float, xa: float, goals: int, assists: int, minutes: int) -> str | None:
        """Return 'HIGH_VALUE', 'OVERPERFORMING', or None based on xG+xA vs G+A ratio."""
        total_output = goals + assists
        if total_output == 0:
            if (xg + xa) > 0 and minutes > 450:
                return "HIGH_VALUE"
            return None
        ratio = (xg + xa) / total_output
        if ratio > 1.2 and minutes > 450:
            return "HIGH_VALUE"
        if ratio < 0.8 and minutes > 450:
            return "OVERPERFORMING"
        return None

    def get_ratio(self, xg: float, xa: float, goals: int, assists: int) -> float | None:
        """Return (xG+xA)/(G+A) rounded to 4 decimal places, or None if G+A is zero."""
        total = goals + assists
        if total == 0:
            return None
        return round((xg + xa) / total, 4)
