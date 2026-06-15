from app.domain.models import Stats, Score, CompetitionEntry, PlayerDTO, AggregatedScores
from app.domain.player_assembler import aggregate_stats, build_player, merge


def _make_entry(comp: str, goals: int = 1) -> CompetitionEntry:
    stats = Stats(goals=goals, minutes=500)
    score = Score(offensive=float(goals), defensive=0.0, tactical=0.0, s_final=float(goals))
    return CompetitionEntry(competition=comp, stats=stats, scores=score)


def _make_player(
    name: str = "Test Player",
    comp: str = "England Premier League",
    sofascore_id: str | None = None,
    photo_url: str = "",
    goals: int = 1,
) -> PlayerDTO:
    entry = _make_entry(comp, goals=goals)
    meta = {
        "sofascore_player_id": sofascore_id,
        "name": name,
        "position": "FW",
        "position_exact": "ST",
        "team": "Arsenal",
        "nationality": "English",
        "photo_url": photo_url,
    }
    return build_player(meta, [entry], "2025-2026")


# ── aggregate_stats ─────────────────────────────────────────────────────────


def test_aggregate_stats_sums_goals() -> None:
    entries = [
        _make_entry("England Premier League", goals=3),
        _make_entry("UEFA Champions League", goals=2),
    ]
    agg = aggregate_stats(entries)
    assert agg.goals == 5


def test_aggregate_stats_max_rating() -> None:
    e1 = _make_entry("England Premier League")
    e1.stats.rating = 7.5
    e2 = _make_entry("UEFA Champions League")
    e2.stats.rating = 8.2
    agg = aggregate_stats([e1, e2])
    assert agg.rating == 8.2


# ── merge ────────────────────────────────────────────────────────────────────


def test_merge_none_existing_returns_incoming() -> None:
    incoming = _make_player()
    result = merge(None, incoming)
    assert result.name == incoming.name
    assert len(result.competitions) == 1


def test_merge_appends_new_competition() -> None:
    """Player in PL loaded first, then UCL loaded later → one doc with 2 entries."""
    pl_player = _make_player(comp="England Premier League", goals=5)
    ucl_player = _make_player(comp="UEFA Champions League", goals=2)
    result = merge(pl_player, ucl_player)
    comp_names = {e.competition for e in result.competitions}
    assert "England Premier League" in comp_names
    assert "UEFA Champions League" in comp_names
    assert result.aggregated_stats.goals == 7  # 5 + 2


def test_merge_replaces_same_competition() -> None:
    """Re-loading the same competition updates in place — no duplicate."""
    original = _make_player(comp="England Premier League", goals=3)
    updated = _make_player(comp="England Premier League", goals=10)
    result = merge(original, updated)
    assert len(result.competitions) == 1
    assert result.aggregated_stats.goals == 10


def test_merge_alias_same_competition() -> None:
    """'EPL' and 'England Premier League' are the same canonical competition."""
    epl_player = _make_player(comp="EPL", goals=4)
    updated = _make_player(comp="England Premier League", goals=8)
    result = merge(epl_player, updated)
    assert len(result.competitions) == 1
    assert result.aggregated_stats.goals == 8


def test_merge_linked_player_supersedes_unlinked() -> None:
    """Player with sofascore_id + photo_url supersedes an unlinked (id-less) entry."""
    unlinked = _make_player(sofascore_id=None, photo_url="")
    linked = _make_player(sofascore_id="12345", photo_url="https://example.com/pic.jpg")
    result = merge(unlinked, linked)
    assert result.sofascore_player_id == "12345"
    assert result.photo_url == "https://example.com/pic.jpg"


def test_merge_preserves_existing_id_when_incoming_lacks_it() -> None:
    """If incoming has no sofascore_id but existing does, keep the existing one."""
    existing = _make_player(sofascore_id="99999")
    incoming = _make_player(sofascore_id=None, comp="UEFA Champions League")
    result = merge(existing, incoming)
    assert result.sofascore_player_id == "99999"
