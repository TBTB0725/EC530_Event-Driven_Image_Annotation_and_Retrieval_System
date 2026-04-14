from __future__ import annotations

from app.events import TOPIC_IMAGE_SUBMITTED, make_event


class EventGenerator:
    def generate_valid_image_submitted(self) -> str:
        event = make_event(
            topic=TOPIC_IMAGE_SUBMITTED,
            producer="event_generator",
            payload={
                "image_id": "img_test_001",
                "path": "storage/images/img_test_001.jpg",
                "source": "generated_test",
            },
        )
        return event.to_json()
