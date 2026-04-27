"""Shared Redis channel definitions plus a lightweight event generator.

This module serves two roles:
1. Define the communication contract between services.
2. Provide a small utility for publishing sample events directly into Redis so
   individual services can be tested without running the whole pipeline.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from uuid import uuid4

import redis


REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0


MONGO_URI = "mongodb://localhost:27017"
MONGO_DATABASE_NAME = "image_annotation_system"
MONGO_DOCUMENT_COLLECTION = "image_records"


# Channels used by the project pipeline.
IMAGE_UPLOAD_CHANNEL = "image_upload_channel"
ANNOTATION_REQUEST_CHANNEL = "annotation_request_channel"
DOCUMENT_DB_CHANNEL = "document_db_channel"
EMBEDDING_REQUEST_CHANNEL = "embedding_request_channel"
VECTOR_INDEX_CHANNEL = "vector_index_channel"
VECTOR_QUERY_CHANNEL = "vector_query_channel"
CLI_RESULT_CHANNEL = "cli_result_channel"


# Event names used inside JSON payloads.
UPLOAD_IMAGE_EVENT = "upload_image"
ANNOTATE_IMAGE_EVENT = "annotate_image"
STORE_ANNOTATION_EVENT = "store_annotation"
EMBED_IMAGE_EVENT = "embed_image"
INDEX_EMBEDDING_EVENT = "index_embedding"
QUERY_BY_TOPIC_EVENT = "query_by_topic"
QUERY_SIMILAR_IMAGES_EVENT = "query_similar_images"
QUERY_RESULT_EVENT = "query_result"


def build_event_metadata():
    """Generate a lightweight event envelope for observability.

    Each published message gets a unique event ID plus a UTC timestamp so
    services can trace, log, and eventually deduplicate events more reliably.
    """

    return {
        "event_id": f"evt_{uuid4().hex}",
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def _create_redis_client():
    """Create the shared Redis client used by the event generator."""

    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def build_upload_event(image_path="C:/images/sample.png"):
    """Build a sample CLI -> uploader event."""

    return {
        "event_name": UPLOAD_IMAGE_EVENT,
        "image_path": image_path,
        **build_event_metadata(),
    }


def build_annotation_request_event(
    image_id="img_sample_001",
    stored_image_path="app/storage/image_db/img_sample_001.png",
):
    """Build a sample uploader -> annotation event."""

    return {
        "event_name": ANNOTATE_IMAGE_EVENT,
        "image_id": image_id,
        "stored_image_path": stored_image_path,
        **build_event_metadata(),
    }


def build_store_annotation_event(
    image_id="img_sample_001",
    image_path="app/storage/image_db/img_sample_001.png",
):
    """Build a sample annotation -> document DB event."""

    return {
        "event_name": STORE_ANNOTATION_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        "objects": [
            {"label": "car", "bbox": [12, 44, 180, 200], "conf": 0.93},
            {"label": "person", "bbox": [230, 50, 286, 210], "conf": 0.88},
        ],
        "review": {
            "status": "pending",
            "notes": "",
        },
        **build_event_metadata(),
    }


def build_embed_image_event(
    image_id="img_sample_001",
    image_path="app/storage/image_db/img_sample_001.png",
):
    """Build a sample document DB -> embedding event."""

    return {
        "event_name": EMBED_IMAGE_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        **build_event_metadata(),
    }


def build_index_embedding_event(
    image_id="img_sample_001",
    image_path="app/storage/image_db/img_sample_001.png",
    embedding=None,
):
    """Build a sample embedding -> vector index event."""

    if embedding is None:
        embedding = [0.11, 0.22, 0.33, 0.44]

    return {
        "event_name": INDEX_EMBEDDING_EVENT,
        "image_id": image_id,
        "image_path": image_path,
        "embedding": embedding,
        **build_event_metadata(),
    }


def build_topic_query_event(topic="car", top_k=5):
    """Build a sample CLI -> vector index topic query event."""

    return {
        "event_name": QUERY_BY_TOPIC_EVENT,
        "topic": topic,
        "top_k": top_k,
        **build_event_metadata(),
    }


def build_similarity_query_event(
    image_path="C:/images/query.png",
    top_k=5,
):
    """Build a sample CLI -> vector index image similarity event."""

    return {
        "event_name": QUERY_SIMILAR_IMAGES_EVENT,
        "image_path": image_path,
        "top_k": top_k,
        **build_event_metadata(),
    }


def build_query_result_event(
    source_event_name=QUERY_BY_TOPIC_EVENT,
    results=None,
):
    """Build a sample vector index -> CLI query result event."""

    if results is None:
        results = [
            {
                "image_id": "img_sample_001",
                "score": 0.97,
                "image_path": "app/storage/image_db/img_sample_001.png",
            }
        ]

    return {
        "event_name": QUERY_RESULT_EVENT,
        "source_event_name": source_event_name,
        "results": results,
        **build_event_metadata(),
    }


EVENT_CHANNELS = {
    UPLOAD_IMAGE_EVENT: IMAGE_UPLOAD_CHANNEL,
    ANNOTATE_IMAGE_EVENT: ANNOTATION_REQUEST_CHANNEL,
    STORE_ANNOTATION_EVENT: DOCUMENT_DB_CHANNEL,
    EMBED_IMAGE_EVENT: EMBEDDING_REQUEST_CHANNEL,
    INDEX_EMBEDDING_EVENT: VECTOR_INDEX_CHANNEL,
    QUERY_BY_TOPIC_EVENT: VECTOR_QUERY_CHANNEL,
    QUERY_SIMILAR_IMAGES_EVENT: VECTOR_QUERY_CHANNEL,
    QUERY_RESULT_EVENT: CLI_RESULT_CHANNEL,
}


EVENT_BUILDERS = {
    UPLOAD_IMAGE_EVENT: build_upload_event,
    ANNOTATE_IMAGE_EVENT: build_annotation_request_event,
    STORE_ANNOTATION_EVENT: build_store_annotation_event,
    EMBED_IMAGE_EVENT: build_embed_image_event,
    INDEX_EMBEDDING_EVENT: build_index_embedding_event,
    QUERY_BY_TOPIC_EVENT: build_topic_query_event,
    QUERY_SIMILAR_IMAGES_EVENT: build_similarity_query_event,
    QUERY_RESULT_EVENT: build_query_result_event,
}


def build_sample_event(
    event_name,
    image_id="img_sample_001",
    image_path="app/storage/image_db/img_sample_001.png",
    topic="car",
    top_k=5,
):
    """Build one sample event by event name.

    The optional arguments let you reuse the generator across services without
    rewriting fixture JSON by hand each time.
    """

    if event_name == UPLOAD_IMAGE_EVENT:
        return build_upload_event(image_path=image_path)
    if event_name == ANNOTATE_IMAGE_EVENT:
        return build_annotation_request_event(
            image_id=image_id,
            stored_image_path=image_path,
        )
    if event_name == STORE_ANNOTATION_EVENT:
        return build_store_annotation_event(
            image_id=image_id,
            image_path=image_path,
        )
    if event_name == EMBED_IMAGE_EVENT:
        return build_embed_image_event(
            image_id=image_id,
            image_path=image_path,
        )
    if event_name == INDEX_EMBEDDING_EVENT:
        return build_index_embedding_event(
            image_id=image_id,
            image_path=image_path,
        )
    if event_name == QUERY_BY_TOPIC_EVENT:
        return build_topic_query_event(topic=topic, top_k=top_k)
    if event_name == QUERY_SIMILAR_IMAGES_EVENT:
        return build_similarity_query_event(image_path=image_path, top_k=top_k)
    if event_name == QUERY_RESULT_EVENT:
        return build_query_result_event(source_event_name=QUERY_BY_TOPIC_EVENT)

    raise ValueError(f"Unsupported event name: {event_name}")


def publish_event(event_name, message, client=None):
    """Publish one event to its configured Redis channel."""

    if client is None:
        client = _create_redis_client()

    channel = EVENT_CHANNELS[event_name]
    client.publish(channel, json.dumps(message))
    return channel


def publish_sample_event(
    event_name,
    image_id="img_sample_001",
    image_path="app/storage/image_db/img_sample_001.png",
    topic="car",
    top_k=5,
    client=None,
):
    """Build and publish one sample event for service-isolated testing."""

    message = build_sample_event(
        event_name=event_name,
        image_id=image_id,
        image_path=image_path,
        topic=topic,
        top_k=top_k,
    )
    channel = publish_event(event_name, message, client=client)
    return channel, message


def list_supported_events():
    """Return all event names supported by the generator utility."""

    return list(EVENT_BUILDERS.keys())


def _build_argument_parser():
    """Create the small CLI used to publish sample events from the terminal."""

    parser = argparse.ArgumentParser(
        description="Publish sample Redis events for one stage of the pipeline."
    )
    parser.add_argument(
        "event_name",
        choices=list_supported_events(),
        help="Which sample event to publish.",
    )
    parser.add_argument(
        "--image-id",
        default="img_sample_001",
        help="Image ID to include in downstream events.",
    )
    parser.add_argument(
        "--image-path",
        default="app/storage/image_db/img_sample_001.png",
        help="Image path to include in the sample event.",
    )
    parser.add_argument(
        "--topic",
        default="car",
        help="Topic string for topic-query events.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k value for retrieval events.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the event JSON without publishing it.",
    )
    return parser


def main():
    """Command-line entrypoint for publishing one sample event."""

    parser = _build_argument_parser()
    args = parser.parse_args()

    message = build_sample_event(
        event_name=args.event_name,
        image_id=args.image_id,
        image_path=args.image_path,
        topic=args.topic,
        top_k=args.top_k,
    )

    if args.print_only:
        print(json.dumps(message, indent=2))
        return

    channel = publish_event(args.event_name, message)
    print(f"Published {args.event_name} to {channel}")
    print(json.dumps(message, indent=2))


if __name__ == "__main__":
    main()
