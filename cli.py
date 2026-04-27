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
    build_event_metadata,
)


def main():
    """Interactive menu for upload and retrieval user flows."""

    exist = True

    while exist:
        user_choice = input(
            "1 Upload image\n"
            "2 Query images by topic\n"
            "3 Query similar images\n"
            "4 Exit\n"
            "Please choose the option: "
        )

        if user_choice == "1":
            user_input = prompt_for_image_path()
            message = package_upload_message(user_input)
            publish_upload_message(message)
        elif user_choice == "2":
            topic = input("Please type the topic: ").strip()
            top_k = prompt_top_k()
            publish_query_message(package_topic_query_message(topic, top_k))
            print_query_results(listen_for_query_results())
        elif user_choice == "3":
            user_input = prompt_for_image_path()
            top_k = prompt_top_k()
            publish_query_message(package_similarity_query_message(user_input, top_k))
            print_query_results(listen_for_query_results())
        elif user_choice == "4":
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
        **build_event_metadata(),
    }


def package_topic_query_message(topic, top_k=5):
    """Build the CLI -> vector index topic query payload."""

    return {
        "event_name": QUERY_BY_TOPIC_EVENT,
        "topic": topic,
        "top_k": top_k,
        **build_event_metadata(),
    }


def package_similarity_query_message(path, top_k=5):
    """Build the CLI -> vector index image similarity query payload."""

    return {
        "event_name": QUERY_SIMILAR_IMAGES_EVENT,
        "image_path": path,
        "top_k": top_k,
        **build_event_metadata(),
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
    """Wait for one asynchronous query result from the vector index service."""

    client = _create_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(CLI_RESULT_CHANNEL)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = json.loads(message["data"])
        if data.get("event_name") == QUERY_RESULT_EVENT:
            return data


def print_query_results(result_message):
    """Render a query result payload in a user-friendly CLI format."""

    if not result_message:
        print("No query result received.")
        return

    print(f"Results for {result_message['source_event_name']}:")
    results = result_message.get("results", [])
    if not results:
        print("No matching images found.")
        return

    for index, result in enumerate(results, start=1):
        image_id = result.get("image_id", "unknown")
        score = result.get("score", 0.0)
        image_path = result.get("image_path", "")
        print(f"{index}. image_id={image_id} score={score:.4f} path={image_path}")


if __name__ == "__main__":
    main()
