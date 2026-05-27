import textwrap
import pytest
from pathlib import Path
from app.infrastructure.kaggle_client import KaggleDatasetClient


@pytest.fixture
def client() -> KaggleDatasetClient:
    return KaggleDatasetClient()


def _write_csv(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.csv"
    p.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
    return p


def test_parse_csv_basic_stats(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Test Player,gb ENG,MF,Arsenal,eng Premier League,1800,10,5,2,3,1,0,,0,4
    """)
    players = client.parse_csv(csv, season="2025-2026")
    assert len(players) == 1
    p = players[0]
    agg = p.aggregated_stats
    assert agg.goals == 10
    assert agg.assists == 5
    assert agg.minutes == 1800
    assert agg.pk_scored == 2
    assert agg.pk_taken == 3
    assert agg.yellow_cards == 1
    assert agg.red_cards == 0
    assert agg.fouls_committed == pytest.approx(4.0)


def test_parse_csv_gk_stats(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Keeper Man,de GER,GK,Bayern,de Bundesliga,2700,0,0,0,0,0,0,12,3,0
    """)
    players = client.parse_csv(csv, season="2025-2026")
    p = players[0]
    assert p.position == "GK"
    assert p.aggregated_stats.clean_sheets == 12
    assert p.aggregated_stats.pk_saved == 3


def test_parse_csv_position_normalization(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Player A,fr FRA,MF,PSG,fr Ligue 1,900,1,2,0,0,0,0,,0,1
        2,Player B,es ESP,DF,Barcelona,es La Liga,900,0,1,0,0,1,0,,0,2
    """)
    players = client.parse_csv(csv, season="2025-2026")
    positions = {p.name: p.position for p in players}
    assert positions["Player A"] == "MF"
    assert positions["Player B"] == "DF"


def test_parse_csv_multi_position_takes_primary(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Dual Player,us USA,"MF,FW",Man City,eng Premier League,900,3,4,0,0,0,0,,0,0
    """)
    players = client.parse_csv(csv, season="2025-2026")
    assert players[0].position == "MF"


def test_parse_csv_competition_name_mapping(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,P1,gb ENG,FW,Liverpool,eng Premier League,900,5,2,0,0,0,0,,0,0
        2,P2,de GER,MF,Dortmund,de Bundesliga,900,2,3,0,0,1,0,,0,1
        3,P3,es ESP,DF,Real Madrid,es La Liga,900,0,1,0,0,0,0,,0,2
        4,P4,fr FRA,MF,Lyon,fr Ligue 1,900,1,4,0,0,0,0,,0,0
        5,P5,it ITA,FW,Napoli,it Serie A,900,6,1,0,0,0,0,,0,0
    """)
    players = client.parse_csv(csv, season="2025-2026")
    comp_map = {p.name: p.competitions[0].competition for p in players}
    assert comp_map["P1"] == "England Premier League"
    assert comp_map["P2"] == "Germany Bundesliga"
    assert comp_map["P3"] == "Spain La Liga"
    assert comp_map["P4"] == "France Ligue 1"
    assert comp_map["P5"] == "Italy Serie A"


def test_parse_csv_nationality_normalized(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Player X,us USA,MF,Chelsea,eng Premier League,900,0,0,0,0,0,0,,0,0
    """)
    players = client.parse_csv(csv, season="2025-2026")
    assert players[0].nationality == "USA"


def test_parse_csv_sofascore_player_id_is_none(tmp_path, client):
    headers = "Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls"
    row = "1,Erling Haaland,no NOR,FW,Man City,eng Premier League,2700,30,5,6,7,1,0,,0,3"
    csv = _write_csv(tmp_path, headers + "\n" + row)
    p = client.parse_csv(csv, season="2025-2026")[0]
    assert p.sofascore_player_id is None


def test_parse_csv_aggregates_multi_competition(tmp_path, client):
    """Same player appearing in two competition rows should produce one PlayerDTO with summed stats."""
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Multi Player,br BRA,FW,Flamengo,eng Premier League,900,5,2,1,2,1,0,,0,2
        2,Multi Player,br BRA,FW,Flamengo,it Serie A,450,3,1,0,1,0,0,,0,1
    """)
    players = client.parse_csv(csv, season="2025-2026")
    assert len(players) == 1
    agg = players[0].aggregated_stats
    assert agg.goals == 8
    assert agg.assists == 3
    assert agg.minutes == 1350
    assert len(players[0].competitions) == 2


def test_parse_csv_season_stored(tmp_path, client):
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Seasonal Player,gb ENG,MF,Everton,eng Premier League,500,1,0,0,0,0,0,,0,0
    """)
    players = client.parse_csv(csv, season="2024-2025")
    assert players[0].season == "2024-2025"


def test_parse_csv_skips_header_repeat_rows(tmp_path, client):
    """FBref CSVs sometimes repeat the header mid-file — these should be skipped."""
    csv = _write_csv(tmp_path, """
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        1,Real Player,gb ENG,MF,Arsenal,eng Premier League,900,2,1,0,0,1,0,,0,0
        Rk,Player,Nation,Pos,Squad,Comp,Min,Gls,Ast,PK,PKatt,CrdY,CrdR,CS,PKsv,Fls
        2,Another Player,de GER,FW,Bayern,de Bundesliga,900,5,2,0,0,0,0,,0,1
    """)
    players = client.parse_csv(csv, season="2025-2026")
    assert len(players) == 2
