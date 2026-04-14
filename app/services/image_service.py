from __future__ import annotations

from app.events import (
    Event,
    TOPIC_IMAGE_SUBMITTED,
    TOPIC_INFERENCE_COMPLETED,
    make_event,
    validate_event,
)
from app.message_bus import MessageBus
from app.storage.image_store import ImageStore


class ImageService:
    def __init__(self, bus: MessageBus, image_store: ImageStore) -> None:
        self.bus = bus
        self.image_store = image_store

    def submit_image(self, source_path: str) -> None:
        image_id, stored_path = self.image_store.save_image(source_path)

        event = make_event(
            topic=TOPIC_IMAGE_SUBMITTED,
            producer="image_service",
            payload={
                "image_id": image_id,
                "path": stored_path,
                "source": "cli_upload",
            },
        )
        self.bus.publish(event)

    def handle_image_submitted(self, event: Event) -> None:
        image_id = event.payload["image_id"]
        path = event.payload["path"]

        annotation_payload = {
            "image_id": image_id,
            "path": path,
            "model_version": "simulator_v1",
            "objects": [
                {
                    "object_id": f"{image_id}_obj_1",
                    "label": "car",
                    "bbox": [10, 20, 100, 120],
                    "confidence": 0.95,
                }
            ],
        }

        out_event = make_event(
            topic=TOPIC_INFERENCE_COMPLETED,
            producer="image_service",
            payload=annotation_payload,
        )
        self.bus.publish(out_event)
