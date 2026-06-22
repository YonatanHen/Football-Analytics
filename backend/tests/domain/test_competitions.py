import pytest

from app.domain.competitions import canonical_competition, classify_competition


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Standard canonical names pass through unchanged
        ("England Premier League", "England Premier League"),
        ("UEFA Champions League", "UEFA Champions League"),
        ("Germany Bundesliga", "Germany Bundesliga"),
        ("Spain La Liga", "Spain La Liga"),
        ("Italy Serie A", "Italy Serie A"),
        ("France Ligue 1", "France Ligue 1"),
        # Common aliases
        ("EPL", "England Premier League"),
        ("Premier League", "England Premier League"),
        ("English Premier League", "England Premier League"),
        ("La Liga", "Spain La Liga"),
        ("LaLiga", "Spain La Liga"),
        ("Bundesliga", "Germany Bundesliga"),
        ("1. Bundesliga", "Germany Bundesliga"),
        ("Serie A", "Italy Serie A"),
        ("Ligue 1", "France Ligue 1"),
        ("Champions League", "UEFA Champions League"),
        ("UCL", "UEFA Champions League"),
        # Country-prefixed aliases
        ("eng Premier League", "England Premier League"),
        ("es La Liga", "Spain La Liga"),
        ("de Bundesliga", "Germany Bundesliga"),
        ("it Serie A", "Italy Serie A"),
        ("fr Ligue 1", "France Ligue 1"),
        # Case-insensitive
        ("england premier league", "England Premier League"),
        ("PREMIER LEAGUE", "England Premier League"),
        # Unknown falls back to original string
        ("MLS", "MLS"),
        ("Eredivisie", "Eredivisie"),
    ],
)
def test_canonical_competition(raw: str, expected: str) -> None:
    assert canonical_competition(raw) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("FIFA World Cup", "national"),
        ("UEFA European Championship", "national"),
        ("CONMEBOL Copa America", "national"),
        ("Africa Cup of Nations", "national"),
        ("UEFA Nations League", "national"),
        ("CONCACAF Gold Cup", "national"),
        ("AFC Asian Cup", "national"),
        ("Olympics Men", "national"),
        ("International Friendly", "national"),
        # club competitions must NOT be mis-classified
        ("England Premier League", "club"),
        ("UEFA Champions League", "club"),
        ("Germany Bundesliga", "club"),
        ("CONCACAF Champions League", "club"),  # club cup — must not match
        ("Spain La Liga", "club"),
        ("Italy Serie A", "club"),
        ("France Ligue 1", "club"),
    ],
)
def test_classify_competition(name: str, expected: str) -> None:
    assert classify_competition(name) == expected
