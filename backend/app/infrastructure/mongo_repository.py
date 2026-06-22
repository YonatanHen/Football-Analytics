from datetime import UTC, datetime

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection

from app.domain.competitions import canonical_competition
from app.domain.models import (
    AggregatedScores,
    CompetitionEntry,
    PlayerDTO,
    Score,
    Stats,
)
from app.infrastructure.text_utils import normalize_text


def _stats_to_dict(stats: Stats) -> dict:
    return {
        "goals": stats.goals,
        "assists": stats.assists,
        "xg": stats.xg,
        "xa": stats.xa,
        "minutes": stats.minutes,
        "clean_sheets": stats.clean_sheets,
        "pk_saved": stats.pk_saved,
        "pk_won": stats.pk_won,
        "pk_scored": stats.pk_scored,
        "pk_taken": stats.pk_taken,
        "yellow_cards": stats.yellow_cards,
        "red_cards": stats.red_cards,
        "yellow_red_cards": stats.yellow_red_cards,
        "direct_red_cards": stats.direct_red_cards,
        "fouls_committed": stats.fouls_committed,
        "rating": stats.rating,
        "big_chances_created": stats.big_chances_created,
        "key_passes": stats.key_passes,
        "appearances": stats.appearances,
        "matches_started": stats.matches_started,
        "saves": stats.saves,
        "saves_outside_box": stats.saves_outside_box,
        "goals_conceded": stats.goals_conceded,
        "goals_prevented": stats.goals_prevented,
        "high_claims": stats.high_claims,
        "penalty_conceded": stats.penalty_conceded,
        "penalty_faced": stats.penalty_faced,
        "total_shots": stats.total_shots,
        "shots_on_target": stats.shots_on_target,
        "shots_off_target": stats.shots_off_target,
        "scoring_frequency": stats.scoring_frequency,
        "penalty_miss": stats.penalty_miss,
        "headed_goals": stats.headed_goals,
        "left_foot_goals": stats.left_foot_goals,
        "right_foot_goals": stats.right_foot_goals,
    }


def _stats_from_dict(d: dict) -> Stats:
    return Stats(
        goals=d.get("goals", 0),
        assists=d.get("assists", 0),
        xg=d.get("xg", 0.0),
        xa=d.get("xa", 0.0),
        minutes=d.get("minutes", 0),
        clean_sheets=d.get("clean_sheets", 0),
        pk_saved=d.get("pk_saved", 0),
        pk_won=d.get("pk_won", 0),
        pk_scored=d.get("pk_scored", 0),
        pk_taken=d.get("pk_taken", 0),
        yellow_cards=d.get("yellow_cards", 0),
        red_cards=d.get("red_cards", 0),
        yellow_red_cards=d.get("yellow_red_cards", 0),
        direct_red_cards=d.get("direct_red_cards", 0),
        fouls_committed=d.get("fouls_committed", 0.0),
        rating=d.get("rating", 0.0),
        big_chances_created=d.get("big_chances_created", 0),
        key_passes=d.get("key_passes", 0),
        appearances=d.get("appearances", 0),
        matches_started=d.get("matches_started", 0),
        saves=d.get("saves", 0),
        saves_outside_box=d.get("saves_outside_box", 0),
        goals_conceded=d.get("goals_conceded", 0),
        goals_prevented=d.get("goals_prevented", 0.0),
        high_claims=d.get("high_claims", 0),
        penalty_conceded=d.get("penalty_conceded", 0),
        penalty_faced=d.get("penalty_faced", 0),
        total_shots=d.get("total_shots", 0),
        shots_on_target=d.get("shots_on_target", 0),
        shots_off_target=d.get("shots_off_target", 0),
        scoring_frequency=d.get("scoring_frequency", 0.0),
        penalty_miss=d.get("penalty_miss", 0),
        headed_goals=d.get("headed_goals", 0),
        left_foot_goals=d.get("left_foot_goals", 0),
        right_foot_goals=d.get("right_foot_goals", 0),
    )


def _bio_doc(player: PlayerDTO) -> dict:
    """Build a player_bios document. Only includes non-empty fields."""
    doc: dict = {
        "name": player.name,
        "norm_name": normalize_text(player.name),
    }
    if player.sofascore_player_id:
        doc["sofascore_player_id"] = player.sofascore_player_id
    if player.position:
        doc["position"] = player.position
    if player.position_exact:
        doc["position_exact"] = player.position_exact
    if player.nationality:
        doc["nationality"] = player.nationality
    if player.photo_url:
        doc["photo_url"] = player.photo_url
    return doc


def _stats_doc(player: PlayerDTO, bio_id) -> dict:
    """Build a player_stats document from a PlayerDTO and bio _id."""
    return {
        "player_bio_id": bio_id,
        "season": player.season,
        "team": player.team,
        "norm_team": normalize_text(player.team),
        "competitions": [
            {
                "competition": c.competition,
                "competition_type": c.competition_type,
                "stats": _stats_to_dict(c.stats),
                "scores": {
                    "offensive": c.scores.offensive,
                    "defensive": c.scores.defensive,
                    "tactical": c.scores.tactical,
                    "s_final": c.scores.s_final,
                },
                "raw_stats": c.raw_stats,
                "total_matches": c.total_matches,
            }
            for c in player.competitions
        ],
        "aggregated_stats": _stats_to_dict(player.aggregated_stats),
        "aggregated_scores": {
            "offensive": player.aggregated_scores.offensive,
            "defensive": player.aggregated_scores.defensive,
            "tactical": player.aggregated_scores.tactical,
            "s_final": player.aggregated_scores.s_final,
            "sleeper_ratio": player.aggregated_scores.underpredicted_ratio,
            "sleeper_flag": player.aggregated_scores.underpredicted_flag,
        },
        "low_sample_size": player.low_sample_size,
        "last_updated": player.last_updated,
    }


def _player_from_docs(bio: dict, stats: dict) -> PlayerDTO:
    """Reconstruct a PlayerDTO from a player_bios + player_stats document pair."""
    comps = []
    for c in stats.get("competitions", []):
        s = c["scores"]
        comps.append(
            CompetitionEntry(
                competition=c["competition"],
                competition_type=c.get("competition_type", "club"),
                stats=_stats_from_dict(c["stats"]),
                scores=Score(
                    offensive=s["offensive"],
                    defensive=s["defensive"],
                    tactical=s["tactical"],
                    s_final=s["s_final"],
                ),
                raw_stats=c.get("raw_stats") or {},
                total_matches=c.get("total_matches", 0),
            )
        )
    ag = stats["aggregated_scores"]
    return PlayerDTO(
        sofascore_player_id=bio.get("sofascore_player_id", ""),
        name=bio["name"],
        season=stats["season"],
        position=bio.get("position", "MF"),
        position_exact=bio.get("position_exact", ""),
        team=stats["team"],
        nationality=bio.get("nationality", ""),
        photo_url=bio.get("photo_url", ""),
        competitions=comps,
        aggregated_stats=_stats_from_dict(stats["aggregated_stats"]),
        aggregated_scores=AggregatedScores(
            offensive=ag["offensive"],
            defensive=ag["defensive"],
            tactical=ag["tactical"],
            s_final=ag["s_final"],
            underpredicted_ratio=ag.get("sleeper_ratio"),
            underpredicted_flag=ag.get("sleeper_flag"),
        ),
        low_sample_size=stats["low_sample_size"],
        last_updated=stats["last_updated"],
    )


def _apply_stats_view(players: list[PlayerDTO], stats_view: str) -> list[PlayerDTO]:
    """Re-aggregate and re-score each player's stats for the requested competition view.

    stats_view values:
      'club'     — aggregate only club competition entries
      'national' — aggregate only national-team competition entries
      <name>     — aggregate only the named competition (canonical match)
    Players with zero matching entries are dropped.
    """
    from app.domain.player_assembler import aggregate_stats
    from app.domain.scoring_engine import ScoringEngine
    from app.domain.sleeper_detector import SleeperDetector

    _scoring = ScoringEngine()
    _sleeper = SleeperDetector()

    result: list[PlayerDTO] = []
    for player in players:
        if stats_view in ("club", "national"):
            entries = [e for e in player.competitions if e.competition_type == stats_view]
        else:
            target = canonical_competition(stats_view)
            entries = [e for e in player.competitions if e.competition == target]

        if not entries:
            continue

        agg = aggregate_stats(entries)
        total_possible = sum(e.total_matches for e in entries) * 90
        score = _scoring.calculate(agg, player.position, total_possible)
        result.append(
            PlayerDTO(
                sofascore_player_id=player.sofascore_player_id,
                name=player.name,
                season=player.season,
                position=player.position,
                position_exact=player.position_exact,
                team=player.team,
                nationality=player.nationality,
                photo_url=player.photo_url,
                competitions=player.competitions,  # always return full list for PlayerCard
                aggregated_stats=agg,
                aggregated_scores=AggregatedScores(
                    offensive=score.offensive,
                    defensive=score.defensive,
                    tactical=score.tactical,
                    s_final=score.s_final,
                    underpredicted_ratio=_sleeper.get_ratio(agg.xg, agg.xa, agg.goals, agg.assists),
                    underpredicted_flag=_sleeper.classify(
                        agg.xg, agg.xa, agg.goals, agg.assists, agg.minutes
                    ),
                ),
                low_sample_size=agg.minutes < 90,
                last_updated=player.last_updated,
            )
        )
    return result


_FETCH_STATE_ID = "singleton"


class MongoRepository:
    """All MongoDB I/O for the application.

    Collections:
    - player_bios: one doc per player (sofascore_player_id or norm_name key);
      holds identity/bio fields.
    - player_stats: one doc per (player_bio_id, season); holds seasonal stats and scores.
    - fetch_state: single doc tracking the last successful Sofascore fetch (for the cooldown limit).
    """

    def __init__(self, client: MongoClient) -> None:
        self._db = client["football_analytics"]
        self._player_bios: Collection = self._db["player_bios"]
        self._player_stats: Collection = self._db["player_stats"]
        self._fetch_log: Collection = self._db["fetch_log"]
        self._fetch_state: Collection = self._db["fetch_state"]
        self._league_meta: Collection = self._db["league_meta"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._player_bios.create_index(
            [("sofascore_player_id", ASCENDING)],
            unique=True,
            sparse=True,
            name="bios_sofascore_id",
        )
        self._player_bios.create_index([("norm_name", ASCENDING)])
        self._player_stats.create_index(
            [("player_bio_id", ASCENDING), ("season", ASCENDING)],
            unique=True,
            name="stats_bio_season",
        )
        self._player_stats.create_index([("season", ASCENDING)])
        self._player_stats.create_index([("aggregated_scores.s_final", DESCENDING)])

    def _find_or_create_bio(self, player: PlayerDTO):
        """Find or create a player_bios doc; return its _id."""
        bio = _bio_doc(player)

        existing = None
        if player.sofascore_player_id:
            existing = self._player_bios.find_one(
                {"sofascore_player_id": player.sofascore_player_id}, {"_id": 1}
            )

        if existing is None:
            # Check for a name-matched bio with no sofascore_player_id
            existing = self._player_bios.find_one(
                {
                    "$or": [
                        {"norm_name": normalize_text(player.name)},
                        {"name": player.name},
                    ],
                    "sofascore_player_id": {"$exists": False},
                },
                {"_id": 1},
            )

        if existing:
            update = {k: v for k, v in bio.items() if v}
            self._player_bios.update_one({"_id": existing["_id"]}, {"$set": update})
            return existing["_id"]

        return self._player_bios.insert_one(bio).inserted_id

    def find_existing(
        self,
        season: str,
        sofascore_player_id: str | None = None,
        norm_name: str | None = None,
        norm_team: str | None = None,
    ) -> PlayerDTO | None:
        bio = None
        if sofascore_player_id:
            bio = self._player_bios.find_one({"sofascore_player_id": sofascore_player_id})
        if bio is None and norm_name:
            bio = self._player_bios.find_one(
                {
                    "norm_name": norm_name,
                    "sofascore_player_id": {"$exists": False},
                }
            )
        if bio is None:
            return None

        stats_query: dict = {"player_bio_id": bio["_id"], "season": season}
        if norm_team and not sofascore_player_id:
            stats_query["norm_team"] = norm_team
        stats = self._player_stats.find_one(stats_query)
        if stats is None:
            return None
        return _player_from_docs(bio, stats)

    def upsert_player(self, player: PlayerDTO) -> None:
        bio_id = self._find_or_create_bio(player)
        doc = _stats_doc(player, bio_id)
        existing = self._player_stats.find_one(
            {"player_bio_id": bio_id, "season": player.season}, {"_id": 1}
        )
        if existing:
            self._player_stats.update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            self._player_stats.insert_one(doc)

    def upsert_player_bio(self, player_id: str, nationality: str, position_exact: str) -> None:
        """Patch bio fields fetched on demand. Only sets non-empty values."""
        update: dict = {}
        if nationality:
            update["nationality"] = nationality
        if position_exact:
            update["position_exact"] = position_exact
        if update:
            self._player_bios.update_one(
                {"sofascore_player_id": player_id},
                {"$set": update},
            )

    def get_players(
        self,
        season: str,
        position: str | None = None,
        team: str | None = None,
        nationality: str | None = None,
        underpredicted_flag: str | None = None,
        name: str | None = None,
        stats_view: str | None = None,
        sort_by: str = "s_final",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlayerDTO], int]:
        # Resolve bio-level filters to a set of bio _ids
        bio_query: dict = {}
        if position:
            bio_query["position"] = position
        if nationality:
            bio_query["nationality"] = nationality
        if name:
            bio_query["name"] = {"$regex": name, "$options": "i"}

        stats_query: dict = {"season": season}
        if bio_query:
            bio_ids = [d["_id"] for d in self._player_bios.find(bio_query, {"_id": 1})]
            stats_query["player_bio_id"] = {"$in": bio_ids}
        if team:
            stats_query["team"] = team
        if underpredicted_flag:
            stats_query["aggregated_scores.sleeper_flag"] = underpredicted_flag

        # When stats_view is set we re-aggregate in Python; fetch all matches and paginate later.
        if stats_view and stats_view != "all":
            all_stats_docs = list(self._player_stats.find(stats_query))
            bio_ids_all = [d["player_bio_id"] for d in all_stats_docs]
            bio_map = {d["_id"]: d for d in self._player_bios.find({"_id": {"$in": bio_ids_all}})}
            players_all = _apply_stats_view(
                [
                    _player_from_docs(bio_map[s["player_bio_id"]], s)
                    for s in all_stats_docs
                    if s["player_bio_id"] in bio_map
                ],
                stats_view,
            )
            sort_dir = -1 if order == "desc" else 1
            players_all.sort(key=lambda p: p.aggregated_scores.s_final * sort_dir)
            total = len(players_all)
            skip = (page - 1) * page_size
            return players_all[skip : skip + page_size], total

        sort_field = f"aggregated_scores.{sort_by}" if sort_by == "s_final" else sort_by
        sort_dir = DESCENDING if order == "desc" else ASCENDING
        total = self._player_stats.count_documents(stats_query)
        skip = (page - 1) * page_size
        stats_docs = list(
            self._player_stats.find(stats_query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(page_size)
        )

        bio_ids_page = [d["player_bio_id"] for d in stats_docs]
        bio_map = {d["_id"]: d for d in self._player_bios.find({"_id": {"$in": bio_ids_page}})}

        players = []
        for stats in stats_docs:
            bio = bio_map.get(stats["player_bio_id"])
            if bio:
                players.append(_player_from_docs(bio, stats))
        return players, total

    def get_competition_list(self, season: str) -> dict[str, list[str]]:
        """Return distinct men's competition names grouped by type for the given season."""
        pipeline = [
            {"$match": {"season": season}},
            {"$unwind": "$competitions"},
            {
                "$group": {
                    "_id": {
                        "name": "$competitions.competition",
                        "type": {"$ifNull": ["$competitions.competition_type", "club"]},
                    }
                }
            },
            {"$sort": {"_id.name": 1}},
        ]
        out: dict[str, list[str]] = {"club": [], "national": []}
        for doc in self._player_stats.aggregate(pipeline):
            t = doc["_id"].get("type", "club")
            out.setdefault(t, []).append(doc["_id"]["name"])
        return out

    def get_player(self, player_id: str, season: str) -> PlayerDTO | None:
        bio = self._player_bios.find_one({"sofascore_player_id": player_id})
        if bio is None:
            return None
        stats = self._player_stats.find_one({"player_bio_id": bio["_id"], "season": season})
        if stats is None:
            return None
        return _player_from_docs(bio, stats)

    def get_scatter_data(self, season: str) -> list[dict]:
        stats_docs = list(
            self._player_stats.find(
                {"season": season},
                {
                    "player_bio_id": 1,
                    "aggregated_stats.xg": 1,
                    "aggregated_stats.xa": 1,
                    "aggregated_stats.goals": 1,
                    "aggregated_stats.assists": 1,
                },
            )
        )
        bio_ids = [d["player_bio_id"] for d in stats_docs]
        bio_map = {
            d["_id"]: d
            for d in self._player_bios.find(
                {"_id": {"$in": bio_ids}},
                {"name": 1, "position": 1, "sofascore_player_id": 1},
            )
        }
        result = []
        for s in stats_docs:
            bio = bio_map.get(s["player_bio_id"], {})
            result.append(
                {
                    "sofascore_player_id": bio.get("sofascore_player_id"),
                    "name": bio.get("name", ""),
                    "position": bio.get("position", ""),
                    "aggregated_stats": s.get("aggregated_stats", {}),
                }
            )
        return result

    def get_last_fetch(self) -> dict | None:
        """Return the singleton fetch-state doc, or None if no fetch has succeeded yet."""
        return self._fetch_state.find_one({"_id": _FETCH_STATE_ID})

    def set_last_fetch(self, competition: str, season: str, at: datetime) -> None:
        """Record the most recent successful Sofascore fetch (upserts the singleton doc).

        Stores the timestamp as an ISO string to keep timezone info across pymongo round-trips.
        """
        self._fetch_state.update_one(
            {"_id": _FETCH_STATE_ID},
            {
                "$set": {
                    "last_fetched_at": at.isoformat(),
                    "last_competition": competition,
                    "last_season": season,
                }
            },
            upsert=True,
        )

    def get_league_total_matches(self, season: str) -> dict[str, int]:
        """Return {competition: total_matches} for all known leagues in a season."""
        return {
            doc["competition"]: doc["total_matches"]
            for doc in self._league_meta.find(
                {"season": season}, {"competition": 1, "total_matches": 1}
            )
        }

    def set_league_total_matches(self, competition: str, season: str, total_matches: int) -> None:
        """Persist total matches played for a (competition, season) pair (upsert)."""
        self._league_meta.update_one(
            {"competition": competition, "season": season},
            {"$set": {"total_matches": total_matches, "updated_at": datetime.now(UTC).isoformat()}},
            upsert=True,
        )

    def log_fetch(
        self, season: str, competitions: list[str], players_upserted: int, status: str
    ) -> dict:
        entry: dict = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "season": season,
            "competitions_fetched": competitions,
            "sources": ["sofascore"],
            "status": status,
            "players_upserted": players_upserted,
        }
        result = self._fetch_log.insert_one(entry)
        entry["_id"] = str(result.inserted_id)
        return entry
