"""Annotation service communication layer."""

from __future__ import annotations

import json

import redis

try:
    from app.services.event_generator import (
        ANNOTATE_IMAGE_EVENT,
        ANNOTATION_REQUEST_CHANNEL,
        DOCUMENT_DB_CHANNEL,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        STORE_ANNOTATION_EVENT,
    )
except ModuleNotFoundError:
    from event_generator import (
        ANNOTATE_IMAGE_EVENT,
        ANNOTATION_REQUEST_CHANNEL,
        DOCUMENT_DB_CHANNEL,
        REDIS_DB,
        REDIS_HOST,
        REDIS_PORT,
        STORE_ANNOTATION_EVENT,
    )


def main():
    """Subscribe to annotation requests and forward results."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(ANNOTATION_REQUEST_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        handle_annotation_event(data)


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def run_annotation(image_path):
    """Placeholder annotation function.

    The model logic is intentionally not implemented yet. This function exists
    so the Redis communication flow can be wired before the YOLO step is added.
    """

    return []


def handle_annotation_event(data):
    """Handle a single annotation request and publish document data."""

    if data.get("event_name") != ANNOTATE_IMAGE_EVENT:
        return None

    annotations = run_annotation(data["stored_image_path"])
    message = package_document_message(
        image_id=data["image_id"],
        image_path=data["stored_image_path"],
        annotations=annotations,
    )
    publish_document_message(message)
    return message


def package_document_message(image_id, image_path, annotations):
    """Build the annotation -> document DB payload."""

    return {
        "event_name": STORE_ANNOTATION_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        "annotations": annotations,
    }


def publish_document_message(message):
    """Publish annotation output to the document DB service."""

    client = _create_redis_client()
    client.publish(DOCUMENT_DB_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
