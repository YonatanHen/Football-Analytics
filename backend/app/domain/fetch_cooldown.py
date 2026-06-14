from datetime import datetime, timedelta


def cooldown_status(
    last_fetched_at: datetime | None,
    now: datetime,
    cooldown_hours: int,
) -> dict:
    """Pure cooldown computation for the once-per-window fetch limit.

    Returns a dict with:
    - allowed: True when there is no prior fetch, or the window has fully elapsed.
    - last_fetched_at / next_allowed_at: datetimes (or None when no prior fetch).
    - seconds_remaining: whole seconds until allowed (0 when allowed).

    Both datetimes must share the same awareness (both tz-aware or both naive).
    """
    if last_fetched_at is None:
        return {
            "allowed": True,
            "last_fetched_at": None,
            "next_allowed_at": None,
            "seconds_remaining": 0,
        }
    next_allowed_at = last_fetched_at + timedelta(hours=cooldown_hours)
    remaining = (next_allowed_at - now).total_seconds()
    return {
        "allowed": remaining <= 0,
        "last_fetched_at": last_fetched_at,
        "next_allowed_at": next_allowed_at,
        "seconds_remaining": max(0, int(remaining)),
    }
