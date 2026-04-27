from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from tests._helpers import assert_has_event_metadata, load_module, require_attr


class EmbeddingServiceTestCase(unittest.TestCase):
    """Contract tests for the CLIP embedding stage.

    This service turns stored images into vectors and hands them off to the
    vector index service.
    """

    def setUp(self):
        self.module = load_module("app/services/embedding_service.py", "embedding_under_test")

    def test_embedding_service_contract_exposes_core_functions(self):
        # These names define the minimum API expected by the rest of the
        # project and by the tests that document the pipeline.
        require_attr(self, self.module, "generate_image_embedding")
        require_attr(self, self.module, "package_index_message")
        require_attr(self, self.module, "publish_index_message")
        require_attr(self, self.module, "handle_embedding_event")

    def test_index_message_contract(self):
        package_index_message = require_attr(self, self.module, "package_index_message")

        message = package_index_message(
            image_id="img-123",
            image_path="app/storage/image_db/img-123.png",
            embedding=[0.1, 0.2, 0.3],
        )

        # This payload is the embedding -> vector index contract.
        self.assertEqual(message["event_name"], "index_embedding")
        self.assertEqual(message["image_id"], "img-123")
        self.assertEqual(message["image_path"], "app/storage/image_db/img-123.png")
        self.assertEqual(message["embedding"], [0.1, 0.2, 0.3])
        assert_has_event_metadata(self, message)

    def test_publish_index_message_uses_vector_index_channel(self):
        publish_index_message = require_attr(self, self.module, "publish_index_message")
        fake_client = MagicMock()
        message = {
            "event_name": "index_embedding",
            "image_id": "img-123",
            "image_path": "app/storage/image_db/img-123.png",
            "embedding": [0.1, 0.2, 0.3],
        }

        with patch.object(self.module.redis, "Redis", return_value=fake_client):
            publish_index_message(message)

        # Indexing should be decoupled from embedding through an explicit
        # message handoff.
        fake_client.publish.assert_called_once_with(
            "vector_index_channel",
            json.dumps(message),
        )

    def test_handle_embedding_event_generates_embedding_and_publishes_index_request(self):
        handle_embedding_event = require_attr(self, self.module, "handle_embedding_event")

        with patch.object(
            self.module, "generate_image_embedding", return_value=[0.25, 0.5, 0.75]
        ) as generate_mock, patch.object(
            self.module, "publish_index_message"
        ) as publish_mock:
            handle_embedding_event(
                {
                    "event_name": "embed_image",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                }
            )

        # This test captures the service's orchestration role: compute vector,
        # then send one indexing event downstream.
        generate_mock.assert_called_once_with("app/storage/image_db/img-123.png")
        published_message = publish_mock.call_args.args[0]
        self.assertEqual(published_message["event_name"], "index_embedding")
        self.assertEqual(published_message["image_id"], "img-123")
        self.assertEqual(published_message["image_path"], "app/storage/image_db/img-123.png")
        self.assertEqual(published_message["embedding"], [0.25, 0.5, 0.75])
        assert_has_event_metadata(self, published_message)
