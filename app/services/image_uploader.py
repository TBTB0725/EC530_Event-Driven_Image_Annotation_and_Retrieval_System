"""Redis-driven image uploader service."""

from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import redis

from app.services.event_generator import (
    ANNOTATE_IMAGE_EVENT,
    ANNOTATION_REQUEST_CHANNEL,
    IMAGE_UPLOAD_CHANNEL,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    UPLOAD_IMAGE_EVENT,
    build_event_metadata,
)


def main():
    """Subscribe to upload requests and forward stored-image events."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(IMAGE_UPLOAD_CHANNEL)

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            handle_upload_event(data)
    except KeyboardInterrupt:
        # This keeps the service pleasant to stop during local development.
        print("Image uploader stopped.")
    finally:
        # Close Redis resources when the process exits so the listener can shut
        # down cleanly instead of leaving the connection hanging.
        if hasattr(pubsub, "close"):
            pubsub.close()
        if hasattr(client, "close"):
            client.close()


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def handle_upload_event(data):
    """Handle a single upload event and notify the annotation service.

    For the upload user case, the uploader owns the storage policy:
    it assigns a system-level image ID and stores a copied file under that ID.
    """

    if data.get("event_name") != UPLOAD_IMAGE_EVENT:
        return None

    source_path = Path(data["image_path"])
    image_id = generate_image_id(source_path)
    image_db_path = get_image_db_path()
    stored_image_path = build_stored_image_path(
        image_db_path=image_db_path,
        image_id=image_id,
        source_path=source_path,
    )

    # Content-addressed storage prevents the same image from being copied into
    # the image database multiple times.
    if not stored_image_path.exists():
        shutil.copy2(source_path, stored_image_path)

    message = package_annotation_message(
        image_id=image_id,
        stored_image_path=str(stored_image_path),
    )
    publish_annotation_message(message)
    return message


def package_annotation_message(image_id, stored_image_path):
    """Build the image uploader -> annotation payload."""

    return {
        "event_name": ANNOTATE_IMAGE_EVENT,
        "image_id": image_id,
        "stored_image_path": stored_image_path,
        **build_event_metadata(),
    }


def generate_image_id(source_path):
    """Generate a stable image ID from the file content.

    Using a SHA-256 hash makes duplicate uploads of the same image resolve to
    the same logical image ID instead of creating multiple stored copies.
    """

    hasher = hashlib.sha256()
    with Path(source_path).open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_image_db_path():
    """Return the absolute project path for stored uploaded images."""

    base_path = Path(__file__).resolve().parent.parent
    image_db_path = base_path / "storage" / "image_db"
    image_db_path.mkdir(parents=True, exist_ok=True)
    return image_db_path


def build_stored_image_path(image_db_path, image_id, source_path):
    """Build the stored image path using the system image ID.

    The uploader keeps the original extension but replaces the filename with a
    generated image ID so the storage layer controls identity.
    """

    return image_db_path / f"{image_id}{source_path.suffix.lower()}"


def publish_annotation_message(message):
    """Publish an annotation request."""

    client = _create_redis_client()
    if hasattr(client, "publish"):
        client.publish(ANNOTATION_REQUEST_CHANNEL, json.dumps(message))
    return message


if __name__ == "__main__":
    main()
