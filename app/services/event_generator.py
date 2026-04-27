"""Shared Redis channel and event definitions for the service pipeline.

This module is intentionally small: it only defines the communication contract
between services. Business logic stays inside each service module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0


MONGO_URI = "mongodb://localhost:27017"
MONGO_DATABASE_NAME = "image_annotation_system"
MONGO_DOCUMENT_COLLECTION = "image_records"


# Channels used by the project pipeline.
IMAGE_UPLOAD_CHANNEL = "image_upload_channel"
ANNOTATION_REQUEST_CHANNEL = "annotation_request_channel"
DOCUMENT_DB_CHANNEL = "document_db_channel"
EMBEDDING_REQUEST_CHANNEL = "embedding_request_channel"
VECTOR_INDEX_CHANNEL = "vector_index_channel"
VECTOR_QUERY_CHANNEL = "vector_query_channel"
CLI_RESULT_CHANNEL = "cli_result_channel"


# Event names used inside JSON payloads.
UPLOAD_IMAGE_EVENT = "upload_image"
ANNOTATE_IMAGE_EVENT = "annotate_image"
STORE_ANNOTATION_EVENT = "store_annotation"
EMBED_IMAGE_EVENT = "embed_image"
INDEX_EMBEDDING_EVENT = "index_embedding"
QUERY_BY_TOPIC_EVENT = "query_by_topic"
QUERY_SIMILAR_IMAGES_EVENT = "query_similar_images"
QUERY_RESULT_EVENT = "query_result"


def build_event_metadata():
    """Generate a lightweight event envelope for observability.

    Each published message gets a unique event ID plus a UTC timestamp so
    services can trace, log, and eventually deduplicate events more reliably.
    """

    return {
        "event_id": f"evt_{uuid4().hex}",
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
