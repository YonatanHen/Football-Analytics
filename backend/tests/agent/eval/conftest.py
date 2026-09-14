import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.infrastructure.mongo_repository import MongoRepository


@pytest.fixture(autouse=True)
def no_web_fallback():
    """Override the agent suite's patch: the eval measures the real web fallback."""
    yield


@pytest.fixture(scope="module")
def live_repo() -> MongoRepository:
    if not settings.gemini_api_key:
        pytest.fail("GEMINI_API_KEY is not set; the eval needs a live model.")
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
    except PyMongoError:
        pytest.fail(f"MongoDB is not reachable at {settings.mongo_uri}; start the stack first.")
    return MongoRepository(client)
