import mongomock
import pytest
from pymongo import MongoClient

from app.infrastructure.mongo_repository import MongoRepository


@pytest.fixture
def mongo_client() -> MongoClient:
    return mongomock.MongoClient()


@pytest.fixture
def repo(mongo_client: MongoClient) -> MongoRepository:
    return MongoRepository(mongo_client)
