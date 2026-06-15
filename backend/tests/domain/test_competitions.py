import pytest
from app.domain.competitions import canonical_competition


@pytest.mark.parametrize("raw,expected", [
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
])
def test_canonical_competition(raw: str, expected: str) -> None:
    assert canonical_competition(raw) == expected
