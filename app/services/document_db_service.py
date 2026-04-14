from __future__ import annotations

from app.events import (
    Event,
    TOPIC_ANNOTATION_CORRECTED,
    TOPIC_ANNOTATION_STORED,
    make_event,
    validate_event,
)
from app.message_bus import MessageBus
from app.storage.document_store import DocumentStore


class DocumentDBService:
    def __init__(self, bus: MessageBus, doc_store: DocumentStore) -> None:
        self.bus = bus
        self.doc_store = doc_store

    def handle_inference_completed(self, event: Event) -> None:
        image_id = event.payload["image_id"]

        self.doc_store.updated_insert_annotation(image_id, event.payload)

        out_event = make_event(
            topic=TOPIC_ANNOTATION_STORED,
            producer="document_db_service",
            payload=event.payload,
        )
        self.bus.publish(out_event)