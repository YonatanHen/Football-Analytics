from app.domain.models import Stats, CompetitionEntry, Score


def test_stats_new_fields_have_defaults():
    s = Stats()
    assert s.appearances == 0
    assert s.matches_started == 0
    assert s.yellow_red_cards == 0
    assert s.direct_red_cards == 0
    assert s.saves == 0
    assert s.goals_prevented == 0.0
    assert s.total_shots == 0
    assert s.shots_on_target == 0
    assert s.headed_goals == 0


def test_competition_entry_raw_stats_defaults_empty():
    entry = CompetitionEntry(competition="Test", stats=Stats(), scores=Score(0, 0, 0, 0))
    assert entry.raw_stats == {}
