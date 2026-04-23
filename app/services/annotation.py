"""Annotation service communication layer."""

from __future__ import annotations

import json
from pathlib import Path

import redis

from app.services.event_generator import (
    ANNOTATE_IMAGE_EVENT,
    ANNOTATION_REQUEST_CHANNEL,
    DOCUMENT_DB_CHANNEL,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    STORE_ANNOTATION_EVENT,
)


YOLO_MODEL_NAME = "yolov8n.pt"


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


def _load_yolo_model():
    """Load a YOLO model lazily so import-time stays lightweight.

    The model is imported only when annotation actually runs. This keeps unit
    tests fast and avoids forcing the dependency to exist just to import the
    module.
    """

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ImportError(
            "ultralytics is required for annotation. Install it with "
            "`pip install -r requirements.txt`."
        ) from exc

    return YOLO(YOLO_MODEL_NAME)


def _normalize_bbox(box_coordinates):
    """Convert YOLO xyxy coordinates into an integer JSON-friendly bbox."""

    return [int(round(value)) for value in box_coordinates]


def _extract_objects_from_result(result):
    """Transform a single YOLO result into document-style object records."""

    objects = []
    names = result.names

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        bbox = _normalize_bbox(box.xyxy[0].tolist())

        objects.append(
            {
                "label": names[class_id],
                "bbox": bbox,
                "conf": round(confidence, 4),
            }
        )

    return objects


def run_annotation(image_path):
    """Run YOLO annotation on an image and return document-style objects."""

    resolved_image_path = Path(image_path)
    model = _load_yolo_model()
    results = model.predict(source=str(resolved_image_path), verbose=False)

    if not results:
        return []

    return _extract_objects_from_result(results[0])


def handle_annotation_event(data):
    """Handle a single annotation request and publish document data."""

    if data.get("event_name") != ANNOTATE_IMAGE_EVENT:
        return None

    objects = run_annotation(data["stored_image_path"])
    message = package_document_message(
        image_id=data["image_id"],
        image_path=data["stored_image_path"],
        objects=objects,
    )
    publish_document_message(message)
    return message


def package_document_message(image_id, image_path, objects):
    """Build the annotation -> document DB payload.

    The payload is shaped like a document-oriented image record so downstream
    persistence can store it directly with minimal transformation.
    """

    return {
        "event_name": STORE_ANNOTATION_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        "objects": objects,
        "review": {
            "status": "pending",
            "notes": "",
        },
    }


def publish_document_message(message):
    """Publish annotation output to the document DB service."""

    client = _create_redis_client()
    client.publish(DOCUMENT_DB_CHANNEL, json.dumps(message))


if __name__ == "__main__":
    main()
