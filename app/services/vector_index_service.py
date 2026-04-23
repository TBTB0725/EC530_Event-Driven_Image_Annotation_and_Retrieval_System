"""Vector index service communication layer."""

from __future__ import annotations

import json

import redis

try:
    from app.services.event_generator import (
        CLI_RESULT_CHANNEL,
        INDEX_EMBEDDING_EVENT,
        QUERY_BY_TOPIC_EVENT,
        QUERY_RESULT_EVENT,
        QUERY_SIMILAR_IMAGES_EVENT,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        VECTOR_INDEX_CHANNEL,
        VECTOR_QUERY_CHANNEL,
    )
except ModuleNotFoundError:
    from event_generator import (
        CLI_RESULT_CHANNEL,
        INDEX_EMBEDDING_EVENT,
        QUERY_BY_TOPIC_EVENT,
        QUERY_RESULT_EVENT,
        QUERY_SIMILAR_IMAGES_EVENT,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        VECTOR_INDEX_CHANNEL,
        VECTOR_QUERY_CHANNEL,
    )


def main():
    """Subscribe to both indexing events and query events."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(VECTOR_INDEX_CHANNEL, VECTOR_QUERY_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        event_name = data.get("event_name")

        if event_name == INDEX_EMBEDDING_EVENT:
            handle_index_event(data)
        elif event_name == QUERY_BY_TOPIC_EVENT:
            results = handle_topic_query_event(data)
            publish_query_result_message(package_query_result_message(event_name, results))
        elif event_name == QUERY_SIMILAR_IMAGES_EVENT:
            results = handle_similarity_query_event(data)
            publish_query_result_message(package_query_result_message(event_name, results))


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def upsert_embedding(image_id, embedding, metadata):
    """Placeholder vector-index persistence hook."""

    return {
        "image_id": image_id,
        "embedding": embedding,
        "metadata": metadata,
    }


def encode_text_query(topic):
    """Placeholder text-query encoder."""

    return [topic]


def search_by_topic(encoded_topic, top_k=5):
    """Placeholder topic-search hook."""

    return []


def search_by_similar_image(image_path, top_k=5):
    """Placeholder image-similarity search hook."""

    return []


def handle_index_event(data):
    """Handle one indexing event."""

    if data.get("event_name") != INDEX_EMBEDDING_EVENT:
        return None

    return upsert_embedding(
        image_id=data["image_id"],
        embedding=data["embedding"],
        metadata={"image_path": data["image_path"]},
    )


def handle_topic_query_event(data):
    """Handle one topic query event."""

    if data.get("event_name") != QUERY_BY_TOPIC_EVENT:
        return []

    encoded_topic = encode_text_query(data["topic"])
    return search_by_topic(encoded_topic, top_k=data.get("top_k", 5))


def handle_similarity_query_event(data):
    """Handle one image similarity query event."""

    if data.get("event_name") != QUERY_SIMILAR_IMAGES_EVENT:
        return []

    return search_by_similar_image(data["image_path"], top_k=data.get("top_k", 5))


def package_query_result_message(source_event_name, results):
    """Build the vector index -> CLI query result payload."""

    return {
        "event_name": QUERY_RESULT_EVENT,
        "source_event_name": source_event_name,
        "results": results,
    }


def publish_query_result_message(message):
    """Publish query results for the CLI or another consumer."""

    client = _create_redis_client()
    client.publish(CLI_RESULT_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
