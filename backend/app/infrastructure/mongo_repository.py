from typing import Optional
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.infrastructure.text_utils import normalize_text


def _stats_to_dict(stats: Stats) -> dict:
    """Serialize a Stats dataclass to a plain dict for MongoDB storage."""
    return {
        "goals": stats.goals, "assists": stats.assists,
        "xg": stats.xg, "xa": stats.xa,
        "minutes": stats.minutes, "clean_sheets": stats.clean_sheets,
        "pk_saved": stats.pk_saved, "pk_won": stats.pk_won,
        "pk_scored": stats.pk_scored, "pk_taken": stats.pk_taken,
        "yellow_cards": stats.yellow_cards, "red_cards": stats.red_cards,
        "fouls_committed": stats.fouls_committed, "rating": stats.rating,
        "big_chances_created": stats.big_chances_created,
        "key_passes": stats.key_passes,
    }


def _stats_from_dict(d: dict) -> Stats:
    """Deserialize a MongoDB document dict back to a Stats dataclass."""
    return Stats(
        goals=d.get("goals", 0), assists=d.get("assists", 0),
        xg=d.get("xg", 0.0), xa=d.get("xa", 0.0),
        minutes=d.get("minutes", 0), clean_sheets=d.get("clean_sheets", 0),
        pk_saved=d.get("pk_saved", 0), pk_won=d.get("pk_won", 0),
        pk_scored=d.get("pk_scored", 0), pk_taken=d.get("pk_taken", 0),
        yellow_cards=d.get("yellow_cards", 0), red_cards=d.get("red_cards", 0),
        fouls_committed=d.get("fouls_committed", 0.0), rating=d.get("rating", 0.0),
        big_chances_created=d.get("big_chances_created", 0),
        key_passes=d.get("key_passes", 0),
    )


def _player_to_doc(player: PlayerDTO) -> dict:
    """Convert a PlayerDTO to a MongoDB document dict (no _id — let MongoDB generate it)."""
    return {
        "sofascore_player_id": player.sofascore_player_id,
        "name": player.name,
        "season": player.season,
        "position": player.position,
        "position_exact": player.position_exact,
        "team": player.team,
        "nationality": player.nationality,
        "photo_url": player.photo_url,
        "competitions": [
            {
                "competition": c.competition,
                "stats": _stats_to_dict(c.stats),
                "scores": {
                    "offensive": c.scores.offensive,
                    "defensive": c.scores.defensive,
                    "tactical": c.scores.tactical,
                    "s_final": c.scores.s_final,
                },
            }
            for c in player.competitions
        ],
        "aggregated_stats": _stats_to_dict(player.aggregated_stats),
        "aggregated_scores": {
            "offensive": player.aggregated_scores.offensive,
            "defensive": player.aggregated_scores.defensive,
            "tactical": player.aggregated_scores.tactical,
            "s_final": player.aggregated_scores.s_final,
            "sleeper_ratio": player.aggregated_scores.sleeper_ratio,
            "sleeper_flag": player.aggregated_scores.sleeper_flag,
        },
        "low_sample_size": player.low_sample_size,
        "last_updated": player.last_updated,
        "norm_name": normalize_text(player.name),
        "norm_team": normalize_text(player.team),
    }


def _player_from_doc(doc: dict) -> PlayerDTO:
    """Reconstruct a PlayerDTO from a MongoDB document dict."""
    comps = []
    for c in doc.get("competitions", []):
        s = c["scores"]
        comps.append(CompetitionEntry(
            competition=c["competition"],
            stats=_stats_from_dict(c["stats"]),
            scores=Score(
                offensive=s["offensive"], defensive=s["defensive"],
                tactical=s["tactical"], s_final=s["s_final"],
            ),
        ))
    ag = doc["aggregated_scores"]
    return PlayerDTO(
        sofascore_player_id=doc.get("sofascore_player_id"),
        name=doc["name"],
        season=doc["season"],
        position=doc["position"],
        position_exact=doc["position_exact"],
        team=doc["team"],
        nationality=doc["nationality"],
        photo_url=doc["photo_url"],
        competitions=comps,
        aggregated_stats=_stats_from_dict(doc["aggregated_stats"]),
        aggregated_scores=AggregatedScores(
            offensive=ag["offensive"], defensive=ag["defensive"],
            tactical=ag["tactical"], s_final=ag["s_final"],
            sleeper_ratio=ag.get("sleeper_ratio"),
            sleeper_flag=ag.get("sleeper_flag"),
        ),
        low_sample_size=doc["low_sample_size"],
        last_updated=doc["last_updated"],
    )


class MongoRepository:
    """All MongoDB I/O for the application: player upserts, queries, and scrape audit logging."""

    def __init__(self, client: MongoClient) -> None:
        """Connect to the football_analytics database and ensure indexes exist."""
        self._db = client["football_analytics"]
        self._players: Collection = self._db["players"]
        self._scrape_log: Collection = self._db["scrape_log"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        existing = {idx["name"] for idx in self._players.list_indexes()}
        if "sofascore_player_id_1_season_1" in existing:
            self._players.drop_index("sofascore_player_id_1_season_1")
        self._players.create_index([("sofascore_player_id", ASCENDING), ("season", ASCENDING)])
        self._players.create_index([("name", ASCENDING), ("team", ASCENDING), ("season", ASCENDING)])
        self._players.create_index([("norm_name", ASCENDING), ("norm_team", ASCENDING), ("season", ASCENDING)])
        self._players.create_index([("season", ASCENDING)])
        self._players.create_index([("aggregated_scores.s_final", DESCENDING)])

    def find_existing(
        self,
        season: str,
        sofascore_player_id: Optional[str] = None,
        norm_name: Optional[str] = None,
        norm_team: Optional[str] = None,
    ) -> Optional[PlayerDTO]:
        """Find an existing player doc.

        Lookup order:
        1. sofascore_player_id + season (any source).
        2. norm_name + norm_team + season WHERE sofascore_player_id IS NULL
           (targets only Kaggle-seeded docs, avoiding collisions between different real players
           who share the same display name on different Sofascore IDs).
        """
        doc = None
        if sofascore_player_id:
            doc = self._players.find_one(
                {"sofascore_player_id": sofascore_player_id, "season": season}
            )
        if doc is None and norm_name and norm_team:
            # Restrict to Kaggle-origin docs (no sofascore_player_id) to avoid false merges
            doc = self._players.find_one(
                {
                    "norm_name": norm_name,
                    "norm_team": norm_team,
                    "season": season,
                    "sofascore_player_id": None,
                }
            )
        return _player_from_doc(doc) if doc else None

    def upsert_player(self, player: PlayerDTO) -> None:
        """Insert or update a player document.

        Matches first by sofascore_player_id+season; if not found and the player has a
        sofascore_player_id, also checks for a Kaggle-origin doc (sofascore_player_id=None)
        with the same norm_name+norm_team+season so a fantasy upsert cleanly overwrites a
        prior Kaggle seed (no duplicate left behind).
        """
        doc = _player_to_doc(player)
        existing_raw = None
        if player.sofascore_player_id:
            existing_raw = self._players.find_one(
                {"sofascore_player_id": player.sofascore_player_id, "season": player.season},
                {"_id": 1},
            )
            if existing_raw is None:
                # Check for a Kaggle-seeded doc (no sofascore_id) for the same player
                existing_raw = self._players.find_one(
                    {
                        "norm_name": normalize_text(player.name),
                        "norm_team": normalize_text(player.team),
                        "season": player.season,
                        "sofascore_player_id": None,
                    },
                    {"_id": 1},
                )
        else:
            # Kaggle player: match by norm_name+norm_team (no sofascore_id to disambiguate)
            existing_raw = self._players.find_one(
                {
                    "norm_name": normalize_text(player.name),
                    "norm_team": normalize_text(player.team),
                    "season": player.season,
                },
                {"_id": 1},
            )
        if existing_raw is not None:
            self._players.update_one({"_id": existing_raw["_id"]}, {"$set": doc})
        else:
            self._players.insert_one(doc)

    def get_players(
        self,
        season: str,
        position: Optional[str] = None,
        team: Optional[str] = None,
        nationality: Optional[str] = None,
        sleeper_flag: Optional[str] = None,
        name: Optional[str] = None,
        sort_by: str = "s_final",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlayerDTO], int]:
        """Return a paginated, filtered, sorted list of players and the total match count."""
        query: dict = {"season": season}
        if position:
            query["position"] = position
        if team:
            query["team"] = team
        if nationality:
            query["nationality"] = nationality
        if sleeper_flag:
            query["aggregated_scores.sleeper_flag"] = sleeper_flag
        if name:
            query["name"] = {"$regex": name, "$options": "i"}

        sort_field = f"aggregated_scores.{sort_by}" if sort_by == "s_final" else sort_by
        sort_dir = DESCENDING if order == "desc" else ASCENDING
        total = self._players.count_documents(query)
        skip = (page - 1) * page_size
        docs = list(
            self._players.find(query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(page_size)
        )
        return [_player_from_doc(d) for d in docs], total

    def get_player(self, player_id: str, season: str) -> Optional[PlayerDTO]:
        """Return a single player by Sofascore ID and season, or None if not found."""
        doc = self._players.find_one({"sofascore_player_id": player_id, "season": season})
        return _player_from_doc(doc) if doc else None

    def get_scatter_data(self, season: str) -> list[dict]:
        """Return minimal player docs (id, name, position, xg/xa/goals/assists) for scatter chart."""
        projection = {
            "name": 1, "position": 1, "sofascore_player_id": 1,
            "aggregated_stats.xg": 1, "aggregated_stats.xa": 1,
            "aggregated_stats.goals": 1, "aggregated_stats.assists": 1,
            "_id": 0,
        }
        return list(self._players.find({"season": season}, projection))

    def log_scrape(
        self, season: str, competitions: list[str], players_upserted: int, status: str
    ) -> dict:
        """Write a scrape audit record and return it with the inserted MongoDB _id."""
        entry: dict = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "season": season,
            "competitions_scraped": competitions,
            "sources": ["sofascore", "fbref"],
            "status": status,
            "players_upserted": players_upserted,
        }
        result = self._scrape_log.insert_one(entry)
        entry["_id"] = str(result.inserted_id)
        return entry
