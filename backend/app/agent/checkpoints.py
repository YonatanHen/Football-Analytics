"""Chat session storage: one checkpoint document per session, expired by TTL."""

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.config import settings


def build_checkpointer(mongo_client: MongoClient) -> MongoDBSaver:
    """Mongo saver whose documents expire `chat_session_ttl_seconds` after their last write."""
    return MongoDBSaver(
        mongo_client,
        db_name="football_analytics",
        checkpoint_collection_name=settings.checkpoint_collection,
        ttl=settings.chat_session_ttl_seconds,
    )


def keep_latest_checkpoint(saver: MongoDBSaver, session_id: str) -> None:
    """Delete every checkpoint of the session except the newest. The library's prune() is a stub."""
    latest = saver.get_tuple({"configurable": {"thread_id": session_id}})
    if latest is None:
        return
    older = {"thread_id": session_id, "checkpoint_id": {"$ne": latest.checkpoint["id"]}}
    saver.checkpoint_collection.delete_many(older)
    saver.writes_collection.delete_many(older)
