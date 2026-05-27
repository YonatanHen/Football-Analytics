import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.domain.scoring_engine import ScoringEngine
from app.domain.sleeper_detector import SleeperDetector
from app.infrastructure.sofascore_client import SofascoreClient
from app.infrastructure.fbref_client import FBrefClient
from app.infrastructure.data_merger import PlayerDataMerger
from app.infrastructure.mongo_repository import MongoRepository

import pandas as pd

logger = logging.getLogger(__name__)


def _aggregate_stats(entries: list[CompetitionEntry]) -> Stats:
    """Sum per-competition Stats across all entries; uses max rating instead of sum."""
    total = Stats()
    for e in entries:
        s = e.stats
        total.goals += s.goals
        total.assists += s.assists
        total.xg += s.xg
        total.xa += s.xa
        total.minutes += s.minutes
        total.clean_sheets += s.clean_sheets
        total.pk_saved += s.pk_saved
        total.pk_won += s.pk_won
        total.pk_scored += s.pk_scored
        total.pk_taken += s.pk_taken
        total.yellow_cards += s.yellow_cards
        total.red_cards += s.red_cards
        total.fouls_committed += s.fouls_committed
        total.rating = max(total.rating, s.rating)
        total.big_chances_created += s.big_chances_created
        total.key_passes += s.key_passes
    return total


class FantasyMode(AnalysisMode):
    """Live scrape mode: fetches Sofascore + FBref per competition, scores players, and upserts to MongoDB."""

    def __init__(self, mongo_client: MongoClient) -> None:
        """Wire up all infrastructure clients and domain services."""
        self._repo = MongoRepository(mongo_client)
        self._scoring = ScoringEngine()
        self._sleeper = SleeperDetector()
        self._sofascore = SofascoreClient()
        self._fbref = FBrefClient()
        self._merger = PlayerDataMerger()

    def get_mode_name(self) -> str:
        """Return the string identifier for this mode."""
        return "fantasy"

    def fetch_data(self, season: str, competitions: list[str]) -> dict:
        """Scrape Sofascore+FBref for each competition, score all players, upsert, and return scrape log."""
        player_entries: dict[str, list[CompetitionEntry]] = {}
        player_meta: dict[str, dict] = {}
        comp_errors: dict[str, str] = {}

        for comp in competitions:
            try:
                ss_df = self._sofascore.fetch(comp, season)
            except Exception as exc:
                logger.warning("Sofascore fetch failed for %s: %s", comp, exc)
                comp_errors[comp] = str(exc)
                continue

            try:
                fb_df = self._fbref.fetch_misc(comp, season)
            except Exception as exc:
                logger.warning("FBref fetch failed for %s: %s", comp, exc)
                fb_df = pd.DataFrame(columns=["player_name", "team", "pk_won"])

            merged = self._merger.merge(ss_df, fb_df)

            for _, row in merged.iterrows():
                pid = str(row.get("sofascore_player_id", "")).strip()
                if not pid:
                    continue

                stats = Stats(
                    goals=int(row.get("goals", 0)),
                    assists=int(row.get("assists", 0)),
                    xg=float(row.get("xg", 0.0)),
                    xa=float(row.get("xa", 0.0)),
                    minutes=int(row.get("minutes", 0)),
                    clean_sheets=int(row.get("clean_sheets", 0)),
                    pk_saved=int(row.get("pk_saved", 0)),
                    pk_won=int(row.get("pk_won", 0)),
                    pk_scored=int(row.get("pk_scored", 0)),
                    pk_taken=int(row.get("pk_taken", 0)),
                    yellow_cards=int(row.get("yellow_cards", 0)),
                    red_cards=int(row.get("red_cards", 0)),
                    fouls_committed=float(row.get("fouls_committed", 0.0)),
                    rating=float(row.get("rating", 0.0)),
                    big_chances_created=int(row.get("big_chances_created", 0)),
                    key_passes=int(row.get("key_passes", 0)),
                )
                position = str(row.get("position", "MF"))
                score = self._scoring.calculate(stats, position)
                entry = CompetitionEntry(competition=comp, stats=stats, scores=score)

                if pid not in player_entries:
                    player_entries[pid] = []
                    player_meta[pid] = {
                        "name": str(row.get("name", "")),
                        "team": str(row.get("team", "")),
                        "nationality": str(row.get("nationality", "")),
                        "position": position,
                        "position_exact": str(row.get("position_exact", "")),
                        "photo_url": str(row.get("photo_url", "")),
                    }
                player_entries[pid].append(entry)

        upserted = 0
        for pid, entries in player_entries.items():
            meta = player_meta[pid]
            agg_stats = _aggregate_stats(entries)
            agg_score = self._scoring.calculate(agg_stats, meta["position"])
            player = PlayerDTO(
                sofascore_player_id=pid,
                name=meta["name"],
                season=season,
                position=meta["position"],
                position_exact=meta["position_exact"],
                team=meta["team"],
                nationality=meta["nationality"],
                photo_url=meta["photo_url"],
                competitions=entries,
                aggregated_stats=agg_stats,
                aggregated_scores=AggregatedScores(
                    offensive=agg_score.offensive,
                    defensive=agg_score.defensive,
                    tactical=agg_score.tactical,
                    s_final=agg_score.s_final,
                    sleeper_ratio=self._sleeper.get_ratio(
                        agg_stats.xg, agg_stats.xa, agg_stats.goals, agg_stats.assists
                    ),
                    sleeper_flag=self._sleeper.classify(
                        agg_stats.xg, agg_stats.xa,
                        agg_stats.goals, agg_stats.assists, agg_stats.minutes,
                    ),
                ),
                low_sample_size=agg_stats.minutes < 90,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            self._repo.upsert_player(player)
            upserted += 1

        log = self._repo.log_scrape(
            season=season,
            competitions=competitions,
            players_upserted=upserted,
            status="success" if not comp_errors else "partial",
        )
        if comp_errors:
            log["competition_errors"] = comp_errors
        return log

    def process(self, season: str) -> list[PlayerDTO]:
        """Return all scored players for the given season from MongoDB."""
        players, _ = self._repo.get_players(season=season)
        return players
