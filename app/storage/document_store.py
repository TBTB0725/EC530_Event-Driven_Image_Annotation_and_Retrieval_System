from __future__ import annotations

from typing import Any, Dict


class DocumentStore:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def updated_insert_annotation(self, image_id: str, record: Dict[str, Any]) -> None:
        self.records[image_id] = record
        print(f"[DocumentStore] Updated and inserted annotation for image_id={image_id}")

    def get_annotation(self, image_id: str) -> Dict[str, Any] | None:
        return self.records.get(image_id)
