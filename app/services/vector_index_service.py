"""Vector index service communication layer."""

from __future__ import annotations

import json
from pathlib import Path

import redis

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
    build_event_metadata,
)
from app.storage.vector_index import (
    search_similar_vectors,
    upsert_embedding as storage_upsert_embedding,
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
    """Persist one embedding into the FAISS-backed storage layer."""

    return storage_upsert_embedding(image_id=image_id, embedding=embedding, metadata=metadata)


def encode_text_query(topic):
    """Encode a topic string into the same CLIP embedding space as images."""

    try:
        import torch
        from transformers import AutoProcessor, CLIPModel
    except ImportError as exc:
        raise ImportError(
            "Vector query requires transformers and torch. Install them with "
            "`pip install -r requirements.txt`."
        ) from exc

    model_name = "openai/clip-vit-base-patch32"
    processor = AutoProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.eval()

    inputs = processor(text=[topic], return_tensors="pt", padding=True)

    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
        normalized_features = text_features / text_features.norm(dim=-1, keepdim=True)

    return normalized_features[0].cpu().tolist()


def search_by_topic(encoded_topic, top_k=5):
    """Search the vector index using a text query embedding."""

    return search_similar_vectors(encoded_topic, top_k=top_k)


def search_by_similar_image(image_path, top_k=5):
    """Search the vector index using an image query embedding."""

    from app.services.embedding_service import generate_image_embedding

    resolved_image_path = Path(image_path)
    query_embedding = generate_image_embedding(str(resolved_image_path))
    return search_similar_vectors(query_embedding, top_k=top_k)


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
        **build_event_metadata(),
    }


def publish_query_result_message(message):
    """Publish query results for the CLI or another consumer."""

    client = _create_redis_client()
    client.publish(CLI_RESULT_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
