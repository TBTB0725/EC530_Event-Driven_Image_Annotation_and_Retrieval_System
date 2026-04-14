from __future__ import annotations

from typing import Callable

import redis

from app.config import REDIS_DECODE_RESPONSES, REDIS_HOST, REDIS_PORT
from app.events import Event


class MessageBus:
    def __init__(self) -> None:
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=REDIS_DECODE_RESPONSES,
        )

    def publish(self, event: Event) -> None:
        self.redis_client.publish(event.topic, event.to_json())
        print(f"[MessageBus] Published -> {event.topic} | event_id={event.event_id}")

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> None:
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(topic)
        print(f"[MessageBus] Subscribed to topic: {topic}")

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                event = Event.from_json(message["data"])
                handler(event)
            except Exception as exc:
                print(f"[MessageBus] Error handling message on {topic}: {exc}")
