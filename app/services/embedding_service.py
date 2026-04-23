"""Embedding service communication layer."""

from __future__ import annotations

import json
from pathlib import Path

import redis

from app.services.event_generator import (
    EMBED_IMAGE_EVENT,
    EMBEDDING_REQUEST_CHANNEL,
    INDEX_EMBEDDING_EVENT,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    VECTOR_INDEX_CHANNEL,
)


CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"


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


def _load_clip_components():
    """Load CLIP processor and model lazily for runtime embedding.

    The imports happen only when embedding is actually requested, which keeps
    unit tests and module import lightweight. The first real run may download
    model weights from Hugging Face if they are not already cached locally.
    """

    try:
        import torch
        from PIL import Image
        from transformers import AutoProcessor, CLIPModel
    except ImportError as exc:
        raise ImportError(
            "Embedding requires transformers, torch, and pillow. Install them "
            "with `pip install -r requirements.txt`."
        ) from exc

    processor = AutoProcessor.from_pretrained(CLIP_MODEL_NAME)
    model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
    model.eval()
    return torch, Image, processor, model


def generate_image_embedding(image_path):
    """Generate a CLIP image embedding and return it as a JSON-safe list.

    The vector is L2-normalized so downstream similarity search can use cosine
    similarity or dot-product style comparisons more consistently.
    """

    torch, image_lib, processor, model = _load_clip_components()
    resolved_image_path = Path(image_path)

    with image_lib.open(resolved_image_path) as raw_image:
        image = raw_image.convert("RGB")

    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
        normalized_features = image_features / image_features.norm(dim=-1, keepdim=True)

    return normalized_features[0].cpu().tolist()


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
