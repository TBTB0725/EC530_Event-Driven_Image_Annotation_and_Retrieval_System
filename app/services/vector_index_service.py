from __future__ import annotations

from app.events import Event, validate_event


class VectorIndexService:
    def __init__(self) -> None:
        self.index: dict[str, dict] = {}

    def handle_embedding_created(self, event: Event) -> None:
        embeddings = event.payload.get("embeddings", [])

        for item in embeddings:
            self.index[item["embedding_id"]] = item

        print(f"[VectorIndexService] Indexed {len(embeddings)} embeddings.")

    def search_by_topic(self, topic_text: str) -> list[dict]:
        print(f"[VectorIndexService] Searching by topic: {topic_text}")
        return list(self.index.values())

    def search_by_image(self, image_path: str) -> list[dict]:
        print(f"[VectorIndexService] Searching by image: {image_path}")
        return list(self.index.values())
