"""User-facing CLI for publishing requests into the Redis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import redis

from app.services.event_generator import (
    CLI_RESULT_CHANNEL,
    IMAGE_UPLOAD_CHANNEL,
    QUERY_BY_TOPIC_EVENT,
    QUERY_RESULT_EVENT,
    QUERY_SIMILAR_IMAGES_EVENT,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    UPLOAD_IMAGE_EVENT,
    VECTOR_QUERY_CHANNEL,
)


def main():
    """Simple interactive menu for publishing upload requests.

    Query publishers are defined below as part of the Redis communication
    contract, but the interactive menu is intentionally kept minimal for now.
    """

    exist = True

    while exist:
        user_choice = input(
            "1 Upload image\n"
            "2 Exit\n"
            "Please choose the option: "
        )

        if user_choice == "1":
            user_input = prompt_for_image_path()
            message = package_upload_message(user_input)
            publish_upload_message(message)
        elif user_choice == "2":
            exist = False
        else:
            print("Unknown option.")


def prompt_for_image_path():
    """Prompt until the user provides a supported existing image path."""

    legal = False

    while not legal:
        user_input = input("Please type the address of the pic: ").strip().strip('"')
        legal = is_legal_path(user_input)
        if not legal:
            print("The path not legal.")

    return user_input


def prompt_top_k():
    """Prompt for a positive top-k integer and default to 5 on bad input."""

    raw_value = input("Please type top-k (default 5): ").strip()
    if not raw_value:
        return 5

    try:
        value = int(raw_value)
    except ValueError:
        print("Invalid top-k value. Using 5.")
        return 5

    if value <= 0:
        print("top-k must be positive. Using 5.")
        return 5

    return value


def is_legal_path(user_input):
    """Validate that the path exists, is a file, and looks like an image."""

    path = Path(user_input)

    if not path.exists():
        return False

    if not path.is_file():
        return False

    if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp"]:
        return False

    return True


def package_upload_message(path):
    """Build the CLI -> image uploader payload."""

    return {
        "event_name": UPLOAD_IMAGE_EVENT,
        "image_path": path,
    }


def package_topic_query_message(topic, top_k=5):
    """Build the CLI -> vector index topic query payload."""

    return {
        "event_name": QUERY_BY_TOPIC_EVENT,
        "topic": topic,
        "top_k": top_k,
    }


def package_similarity_query_message(path, top_k=5):
    """Build the CLI -> vector index image similarity query payload."""

    return {
        "event_name": QUERY_SIMILAR_IMAGES_EVENT,
        "image_path": path,
        "top_k": top_k,
    }


def _create_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )


def publish_upload_message(message):
    """Publish an upload request for the image uploader service."""

    client = _create_redis_client()
    client.publish(IMAGE_UPLOAD_CHANNEL, json.dumps(message))
    print("Upload message published")


def publish_query_message(message):
    """Publish a query request for the vector index service."""

    client = _create_redis_client()
    client.publish(VECTOR_QUERY_CHANNEL, json.dumps(message))
    print("Query message published")


def listen_for_query_results():
    """Optional helper for reading asynchronous vector query results."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(CLI_RESULT_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        if data.get("event_name") == QUERY_RESULT_EVENT:
            print(data)
            return data


if __name__ == "__main__":
    main()
