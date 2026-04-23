"""Document DB service communication layer."""

from __future__ import annotations

import json

import redis

try:
    from app.services.event_generator import (
        DOCUMENT_DB_CHANNEL,
        EMBED_IMAGE_EVENT,
        EMBEDDING_REQUEST_CHANNEL,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        STORE_ANNOTATION_EVENT,
    )
except ModuleNotFoundError:
    from event_generator import (
        DOCUMENT_DB_CHANNEL,
        EMBED_IMAGE_EVENT,
        EMBEDDING_REQUEST_CHANNEL,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        STORE_ANNOTATION_EVENT,
    )


def main():
    """Subscribe to annotation records and request embedding."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(DOCUMENT_DB_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        handle_document_event(data)


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def persist_document(record):
    """Placeholder persistence hook for document metadata."""

    return record


def handle_document_event(data):
    """Handle one document-storage event and trigger embedding."""

    if data.get("event_name") != STORE_ANNOTATION_EVENT:
        return None

    persist_document(
        {
            "image_id": data["image_id"],
            "image_path": data["image_path"],
            "objects": data["objects"],
            "review": data["review"],
        }
    )
    message = package_embedding_message(
        image_id=data["image_id"],
        image_path=data["image_path"],
    )
    publish_embedding_message(message)
    return message


def package_embedding_message(image_id, image_path):
    """Build the document DB -> embedding payload."""

    return {
        "event_name": EMBED_IMAGE_EVENT,
        "image_id": image_id,
        "image_path": image_path,
    }


def publish_embedding_message(message):
    """Publish an embedding request."""

    client = _create_redis_client()
    client.publish(EMBEDDING_REQUEST_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
