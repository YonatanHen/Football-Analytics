"""Re-score every stored player (each competition and the combined score) with the current formula.

Run inside the backend container: python scripts/DB/rescore_players.py
"""

from pymongo import MongoClient

from app.config import settings
from app.domain.player_assembler import rescore_player
from app.infrastructure.mongo_repository import MongoRepository

repo = MongoRepository(MongoClient(settings.mongo_uri))
players, total = repo.get_players(season=settings.season, page=1, page_size=10000)
print(f"Re-scoring {total} players for {settings.season}...")
scores = []
for p in players:
    rescored = rescore_player(p)
    repo.upsert_player(rescored)
    scores.append(rescored.aggregated_scores.s_final)
    scores.extend(e.scores.s_final for e in rescored.competitions)
print(f"Done. s_final range: {min(scores):.2f} .. {max(scores):.2f}")
