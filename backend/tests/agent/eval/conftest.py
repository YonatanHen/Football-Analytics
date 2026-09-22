import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.infrastructure.mongo_repository import MongoRepository


@pytest.fixture(scope="module")
def live_repo() -> MongoRepository:
    if not (settings.gemini_api_key or settings.llm_api_key):
        pytest.fail("No API key is set; the eval needs a live model.")
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
    except PyMongoError:
        pytest.fail(f"MongoDB is not reachable at {settings.mongo_uri}; start the stack first.")
    return MongoRepository(client)
