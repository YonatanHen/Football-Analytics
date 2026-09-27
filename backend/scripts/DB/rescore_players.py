"""Re-score every stored player (each competition and the combined score) in every season.

Run inside the backend container: python scripts/DB/rescore_players.py
"""

import os
import sys

from pymongo import MongoClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import settings  # noqa: E402
from app.infrastructure.mongo_repository import MongoRepository  # noqa: E402
from app.infrastructure.rescore import rescore_all_players  # noqa: E402

repo = MongoRepository(MongoClient(settings.mongo_uri))
print(f"Re-scoring seasons: {', '.join(repo.list_seasons()) or 'none'}")
scores = rescore_all_players(repo)
if scores:
    print(f"Done. {len(scores)} scores, s_final range: {min(scores):.2f} .. {max(scores):.2f}")
else:
    print("Done. No players stored.")
