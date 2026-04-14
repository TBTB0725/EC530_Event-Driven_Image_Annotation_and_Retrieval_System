from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict


TOPIC_IMAGE_SUBMITTED = "image.submitted"
TOPIC_INFERENCE_COMPLETED = "inference.completed"
TOPIC_ANNOTATION_STORED = "annotation.stored"
TOPIC_EMBEDDING_CREATED = "embedding.created"
TOPIC_ANNOTATION_CORRECTED = "annotation.corrected"

ALL_TOPICS = {
    TOPIC_IMAGE_SUBMITTED,
    TOPIC_INFERENCE_COMPLETED,
    TOPIC_ANNOTATION_STORED,
    TOPIC_EMBEDDING_CREATED,
    TOPIC_ANNOTATION_CORRECTED,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    topic: str
    event_id: str
    timestamp: str
    producer: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str) -> "Event":
        obj = json.loads(data)
        return Event(
            topic=obj["topic"],
            event_id=obj["event_id"],
            timestamp=obj["timestamp"],
            producer=obj["producer"],
            payload=obj["payload"],
        )


def make_event(topic: str, producer: str, payload: Dict[str, Any]) -> Event:
    if topic not in ALL_TOPICS:
        raise ValueError(f"Unknown topic: {topic}")

    return Event(
        topic=topic,
        event_id=str(uuid.uuid4()),
        timestamp=utc_now_iso(),
        producer=producer,
        version="1.0",
        payload=payload,
    )


def validate_event(event: Event) -> bool:
    if not event.topic or event.topic not in ALL_TOPICS:
        return False
    if not event.event_id:
        return False
    if not event.timestamp:
        return False
    if not event.producer:
        return False
    if not isinstance(event.payload, dict):
        return False
    return True
