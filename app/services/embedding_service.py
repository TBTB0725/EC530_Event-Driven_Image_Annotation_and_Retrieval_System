"""Embedding service communication layer."""

from __future__ import annotations

import json

import redis

try:
    from app.services.event_generator import (
        EMBED_IMAGE_EVENT,
        EMBEDDING_REQUEST_CHANNEL,
        INDEX_EMBEDDING_EVENT,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        VECTOR_INDEX_CHANNEL,
    )
except ModuleNotFoundError:
    from event_generator import (
        EMBED_IMAGE_EVENT,
        EMBEDDING_REQUEST_CHANNEL,
        INDEX_EMBEDDING_EVENT,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        VECTOR_INDEX_CHANNEL,
    )


def main():
    """Subscribe to embedding requests and forward vectors to the index."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(EMBEDDING_REQUEST_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        handle_embedding_event(data)


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def generate_image_embedding(image_path):
    """Placeholder CLIP embedding hook."""

    return []


def handle_embedding_event(data):
    """Handle one embedding request and publish indexing data."""

    if data.get("event_name") != EMBED_IMAGE_EVENT:
        return None

    embedding = generate_image_embedding(data["image_path"])
    message = package_index_message(
        image_id=data["image_id"],
        image_path=data["image_path"],
        embedding=embedding,
    )
    publish_index_message(message)
    return message


def package_index_message(image_id, image_path, embedding):
    """Build the embedding -> vector index payload."""

    return {
        "event_name": INDEX_EMBEDDING_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        "embedding": embedding,
    }


def publish_index_message(message):
    """Publish an indexing request."""

    client = _create_redis_client()
    client.publish(VECTOR_INDEX_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
