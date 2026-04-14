from __future__ import annotations

import sys

from app.events import (
    TOPIC_ANNOTATION_CORRECTED,
    TOPIC_ANNOTATION_STORED,
    TOPIC_EMBEDDING_CREATED,
    TOPIC_IMAGE_SUBMITTED,
    TOPIC_INFERENCE_COMPLETED,
)
from app.message_bus import MessageBus
from app.services.document_db_service import DocumentDBService
from app.services.embedding_service import EmbeddingService
from app.services.image_service import ImageService
from app.services.vector_index_service import VectorIndexService
from app.storage.document_store import DocumentStore
from app.storage.image_store import ImageStore


def main() -> None:
    bus = MessageBus()
    image_store = ImageStore()
    doc_store = DocumentStore()

    image_service = ImageService(bus, image_store)
    document_service = DocumentDBService(bus, doc_store)
    embedding_service = EmbeddingService(bus)
    vector_service = VectorIndexService()

    command = sys.argv[1]

    if command == "upload":
        image_path = sys.argv[2]
        image_service.submit_image(image_path)

    elif command == "run_image_service":
        bus.subscribe(TOPIC_IMAGE_SUBMITTED, image_service.handle_image_submitted)

    elif command == "run_document_service":
        bus.subscribe(TOPIC_INFERENCE_COMPLETED, document_service.handle_inference_completed)

    elif command == "run_embedding_service":
        bus.subscribe(TOPIC_ANNOTATION_STORED, embedding_service.handle_annotation_stored)

    elif command == "run_vector_service":
        bus.subscribe(TOPIC_EMBEDDING_CREATED, vector_service.handle_embedding_created)

    elif command == "run_correction_listener":
        bus.subscribe(TOPIC_ANNOTATION_CORRECTED, embedding_service.handle_annotation_corrected)

    elif command == "correct":
        image_id = sys.argv[2]
        document_service.correct_annotation(image_id)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
