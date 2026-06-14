from datetime import datetime, timedelta, timezone

from app.domain.fetch_cooldown import cooldown_status

NOW = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)


def test_no_prior_fetch_is_allowed():
    s = cooldown_status(None, NOW, cooldown_hours=24)
    assert s["allowed"] is True
    assert s["last_fetched_at"] is None
    assert s["next_allowed_at"] is None
    assert s["seconds_remaining"] == 0


def test_within_window_is_blocked():
    last = NOW - timedelta(hours=1)
    s = cooldown_status(last, NOW, cooldown_hours=24)
    assert s["allowed"] is False
    assert s["next_allowed_at"] == last + timedelta(hours=24)
    assert s["seconds_remaining"] == 23 * 3600


def test_exactly_at_boundary_is_allowed():
    last = NOW - timedelta(hours=24)
    s = cooldown_status(last, NOW, cooldown_hours=24)
    assert s["allowed"] is True
    assert s["seconds_remaining"] == 0


def test_past_window_is_allowed():
    last = NOW - timedelta(hours=30)
    s = cooldown_status(last, NOW, cooldown_hours=24)
    assert s["allowed"] is True
    assert s["seconds_remaining"] == 0
