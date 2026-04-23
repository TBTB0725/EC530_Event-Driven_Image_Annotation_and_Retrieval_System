"""MongoDB-backed storage helpers for image annotation documents."""

from __future__ import annotations

from copy import deepcopy

from app.services.event_generator import (
    MONGO_DATABASE_NAME,
    MONGO_DOCUMENT_COLLECTION,
    MONGO_URI,
)


def _load_mongo_client():
    """Load MongoClient lazily so module import does not require pymongo."""

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise ImportError(
            "pymongo is required for document database storage. Install it with "
            "`pip install -r requirements.txt`."
        ) from exc

    return MongoClient


def create_client(uri=MONGO_URI):
    """Create a MongoDB client."""

    mongo_client_class = _load_mongo_client()
    return mongo_client_class(uri)


def get_collection(client=None):
    """Get the MongoDB collection that stores image documents."""

    mongo_client = client or create_client()
    return mongo_client[MONGO_DATABASE_NAME][MONGO_DOCUMENT_COLLECTION]


def upsert_image_record(record, collection=None):
    """Insert or update an image document by `image_id`.

    The stored Mongo document keeps `image_id` both as a field and as the
    logical upsert key, which makes downstream lookup straightforward.
    """

    target_collection = collection or get_collection()
    stored_record = deepcopy(record)

    target_collection.update_one(
        {"image_id": stored_record["image_id"]},
        {"$set": stored_record},
        upsert=True,
    )
    return stored_record
