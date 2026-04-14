from __future__ import annotations

from app.events import Event, TOPIC_EMBEDDING_CREATED, make_event, validate_event
from app.message_bus import MessageBus


class EmbeddingService:
    def __init__(self, bus: MessageBus) -> None:
        self.bus = bus

    def handle_annotation_stored(self, event: Event) -> None:
        image_id = event.payload["image_id"]
        path = event.payload["path"]
        objects = event.payload.get("objects", [])

        embeddings = []
        for obj in objects:
            embeddings.append(
                {
                    "embedding_id": f"emb_{obj['object_id']}",
                    "object_id": obj["object_id"],
                    "label": obj["label"],
                    "bbox": obj["bbox"],
                    "vector": [0.1, 0.2, 0.3],
                }
            )

        out_event = make_event(
            topic=TOPIC_EMBEDDING_CREATED,
            producer="embedding_service",
            payload={
                "image_id": image_id,
                "path": path,
                "embeddings": embeddings,
                "embedding_model": "sim_embedding_v1",
            },
        )
        self.bus.publish(out_event)