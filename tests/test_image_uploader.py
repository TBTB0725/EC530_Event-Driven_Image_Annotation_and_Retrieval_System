from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests._helpers import REPO_ROOT, assert_has_event_metadata, load_module, require_attr


class _FakePubSub:
    """Small stand-in for redis-py's PubSub object used in unit tests."""

    def __init__(self, messages):
        self._messages = messages
        self.subscribed_channels = []

    def subscribe(self, *channels):
        self.subscribed_channels.extend(channels)

    def listen(self):
        for message in self._messages:
            yield message


class _FakeRedisClient:
    """Fake Redis client that returns a predefined PubSub instance."""

    def __init__(self, pubsub):
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


class ImageUploaderTestCase(unittest.TestCase):
    """Contract tests for the image uploader service.

    This service is responsible for receiving upload events, copying the image
    into project storage, and then triggering the annotation stage.
    """

    def setUp(self):
        self.module = load_module(
            "app/services/image_uploader.py", "image_uploader_under_test"
        )

    def test_main_subscribes_to_upload_channel(self):
        fake_pubsub = _FakePubSub(messages=[])
        fake_client = _FakeRedisClient(fake_pubsub)

        with patch.object(self.module.redis, "Redis", return_value=fake_client):
            self.module.main()

        self.assertEqual(fake_pubsub.subscribed_channels, ["image_upload_channel"])

    def test_main_ignores_non_message_pubsub_events(self):
        fake_pubsub = _FakePubSub(
            messages=[
                # Redis emits subscription bookkeeping events before business
                # messages. The uploader must ignore them safely.
                {"type": "subscribe", "channel": "image_upload_channel", "data": 1},
            ]
        )
        fake_client = _FakeRedisClient(fake_pubsub)

        with patch.object(self.module.redis, "Redis", return_value=fake_client), patch.object(
            self.module, "generate_image_id", return_value="a" * 64
        ), patch.object(
            self.module.shutil, "copy2"
        ) as copy_mock:
            self.module.main()

        copy_mock.assert_not_called()

    def test_main_copies_uploaded_image_into_project_image_db(self):
        payload = {
            "event_name": "upload_image",
            "image_path": "C:/Users/tester/Desktop/cat.png",
        }
        fake_pubsub = _FakePubSub(
            messages=[
                {
                    "type": "message",
                    "channel": "image_upload_channel",
                    "data": json.dumps(payload),
                }
            ]
        )
        fake_client = _FakeRedisClient(fake_pubsub)

        with patch.object(self.module.redis, "Redis", return_value=fake_client), patch.object(
            self.module, "generate_image_id", return_value="a" * 64
        ), patch.object(
            self.module.shutil, "copy2"
        ) as copy_mock:
            self.module.main()

        # Uploaded files are expected to be copied into the repo-managed image
        # database folder before any later processing begins. The uploader owns
        # the new filename and should replace the original basename with a
        # generated image ID.
        copy_mock.assert_called_once()
        copy_source, copy_destination = copy_mock.call_args.args

        self.assertEqual(copy_source, Path(payload["image_path"]))
        self.assertEqual(copy_destination.parent, REPO_ROOT / "app" / "storage" / "image_db")
        self.assertEqual(copy_destination.suffix, ".png")
        self.assertRegex(copy_destination.stem, r"^[0-9a-f]{64}$")

    def test_handle_upload_event_returns_annotation_message_with_generated_image_id(self):
        handle_upload_event = require_attr(self, self.module, "handle_upload_event")
        payload = {
            "event_name": "upload_image",
            "image_path": "C:/Users/tester/Desktop/cat.png",
        }

        with patch.object(self.module, "generate_image_id", return_value="b" * 64), patch.object(
            self.module.shutil, "copy2"
        ), patch.object(
            self.module, "publish_annotation_message"
        ) as publish_mock:
            message = handle_upload_event(payload)

        # The uploader should generate an image_id exactly once and reuse it in
        # both the stored file path and the next event payload.
        self.assertEqual(message["event_name"], "annotate_image")
        self.assertRegex(message["image_id"], r"^[0-9a-f]{64}$")
        self.assertTrue(message["stored_image_path"].endswith(f'{message["image_id"]}.png'))
        assert_has_event_metadata(self, message)
        publish_mock.assert_called_once_with(message)

    def test_generate_image_id_is_stable_for_same_file_content(self):
        generate_image_id = require_attr(self, self.module, "generate_image_id")

        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = Path(temp_dir) / "first.png"
            second_path = Path(temp_dir) / "second.png"
            first_path.write_bytes(b"same image bytes")
            second_path.write_bytes(b"same image bytes")

            first_id = generate_image_id(first_path)
            second_id = generate_image_id(second_path)

        self.assertEqual(first_id, second_id)

    def test_handle_upload_event_skips_copy_when_same_image_is_already_stored(self):
        handle_upload_event = require_attr(self, self.module, "handle_upload_event")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "cat.png"
            source_path.write_bytes(b"duplicate image bytes")
            existing_storage_dir = Path(temp_dir) / "image_db"
            existing_storage_dir.mkdir()

            image_id = self.module.generate_image_id(source_path)
            existing_stored_path = existing_storage_dir / f"{image_id}.png"
            existing_stored_path.write_bytes(b"duplicate image bytes")

            with patch.object(
                self.module, "get_image_db_path", return_value=existing_storage_dir
            ), patch.object(self.module.shutil, "copy2") as copy_mock, patch.object(
                self.module, "publish_annotation_message"
            ):
                message = handle_upload_event(
                    {
                        "event_name": "upload_image",
                        "image_path": str(source_path),
                    }
                )

        copy_mock.assert_not_called()
        self.assertEqual(message["image_id"], image_id)
        self.assertEqual(message["stored_image_path"], str(existing_stored_path))

    def test_image_uploader_contract_includes_annotation_message_builder(self):
        # After storage, the uploader should hand off to the annotation stage.
        require_attr(self, self.module, "package_annotation_message")

    def test_image_uploader_contract_includes_annotation_publisher(self):
        require_attr(self, self.module, "publish_annotation_message")

    def test_annotation_message_contract(self):
        package_annotation_message = require_attr(
            self, self.module, "package_annotation_message"
        )

        message = package_annotation_message(
            image_id="img-123",
            stored_image_path="app/storage/image_db/img-123.png",
        )

        # This is the handoff contract from uploader -> annotation service.
        self.assertEqual(message["event_name"], "annotate_image")
        self.assertEqual(message["image_id"], "img-123")
        self.assertEqual(message["stored_image_path"], "app/storage/image_db/img-123.png")
        assert_has_event_metadata(self, message)

    def test_publish_annotation_message_uses_annotation_request_channel(self):
        publish_annotation_message = require_attr(self, self.module, "publish_annotation_message")
        fake_client = MagicMock()
        message = {
            "event_name": "annotate_image",
            "image_id": "img-123",
            "stored_image_path": "app/storage/image_db/img-123.png",
        }

        with patch.object(self.module.redis, "Redis", return_value=fake_client):
            publish_annotation_message(message)

        # The channel name documents the intended next hop in the pipeline.
        fake_client.publish.assert_called_once_with(
            "annotation_request_channel",
            json.dumps(message),
        )
