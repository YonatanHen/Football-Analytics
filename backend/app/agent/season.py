"""Calendar season labels ("2026-2027") for resolving "this season" and "last season"."""

from datetime import date

# European club seasons start in August; July is the first pre-season month.
_SEASON_START_MONTH = 7


def calendar_season(today: date) -> str:
    start = today.year if today.month >= _SEASON_START_MONTH else today.year - 1
    return f"{start}-{start + 1}"


def previous_season(season: str) -> str:
    start = int(season.split("-")[0]) - 1
    return f"{start}-{start + 1}"
