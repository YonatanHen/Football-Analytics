"""Re-score every stored player (each competition and the combined score) in every season.

Run inside the backend container: python scripts/DB/rescore_players.py
"""

from pymongo import MongoClient

from app.config import settings
from app.infrastructure.mongo_repository import MongoRepository
from app.infrastructure.rescore import rescore_all_players

repo = MongoRepository(MongoClient(settings.mongo_uri))
print(f"Re-scoring seasons: {', '.join(repo.list_seasons()) or 'none'}")
scores = rescore_all_players(repo)
if scores:
    print(f"Done. {len(scores)} scores, s_final range: {min(scores):.2f} .. {max(scores):.2f}")
else:
    print("Done. No players stored.")
