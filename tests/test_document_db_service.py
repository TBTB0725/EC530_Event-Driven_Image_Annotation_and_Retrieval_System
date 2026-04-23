from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from tests._helpers import load_module, require_attr


class DocumentDBServiceTestCase(unittest.TestCase):
    """Contract tests for storing annotation metadata.

    This service persists annotation records and then triggers embedding on the
    original stored image.
    """

    def setUp(self):
        self.module = load_module(
            "app/services/document_db_service.py", "document_db_service_under_test"
        )

    def test_document_db_service_contract_exposes_core_functions(self):
        # These define the expected top-level responsibilities of the service.
        require_attr(self, self.module, "persist_document")
        require_attr(self, self.module, "package_embedding_message")
        require_attr(self, self.module, "publish_embedding_message")
        require_attr(self, self.module, "handle_document_event")

    def test_embedding_message_contract(self):
        package_embedding_message = require_attr(self, self.module, "package_embedding_message")

        message = package_embedding_message(
            image_id="img-123",
            image_path="app/storage/image_db/img-123.png",
        )

        # After annotation is stored, embedding should only need image identity
        # and path to continue the pipeline.
        self.assertEqual(
            message,
            {
                "event_name": "embed_image",
                "image_id": "img-123",
                "image_path": "app/storage/image_db/img-123.png",
            },
        )

    def test_publish_embedding_message_uses_embedding_request_channel(self):
        publish_embedding_message = require_attr(self, self.module, "publish_embedding_message")
        fake_client = MagicMock()

        with patch.object(self.module.redis, "Redis", return_value=fake_client):
            publish_embedding_message(
                {
                    "event_name": "embed_image",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                }
            )

        # This channel is the explicit handoff from document persistence to the
        # embedding stage.
        fake_client.publish.assert_called_once_with(
            "embedding_request_channel",
            json.dumps(
                {
                    "event_name": "embed_image",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                }
            ),
        )

    def test_handle_document_event_persists_record_and_requests_embedding(self):
        handle_document_event = require_attr(self, self.module, "handle_document_event")

        event = {
            "event_name": "store_annotation",
            "image_id": "img-123",
            "image_path": "app/storage/image_db/img-123.png",
            "annotations": [{"label": "dog", "confidence": 0.97, "bbox": [1, 2, 3, 4]}],
        }

        with patch.object(self.module, "persist_document") as persist_mock, patch.object(
            self.module, "publish_embedding_message"
        ) as publish_mock:
            handle_document_event(event)

        # The document service owns two actions for this event: persist the
        # annotation record, then enqueue embedding.
        persist_mock.assert_called_once_with(
            {
                "image_id": "img-123",
                "image_path": "app/storage/image_db/img-123.png",
                "annotations": [{"label": "dog", "confidence": 0.97, "bbox": [1, 2, 3, 4]}],
            }
        )
        publish_mock.assert_called_once_with(
            {
                "event_name": "embed_image",
                "image_id": "img-123",
                "image_path": "app/storage/image_db/img-123.png",
            }
        )
