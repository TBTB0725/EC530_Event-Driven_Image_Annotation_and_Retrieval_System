from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from tests._helpers import load_module, require_attr


class AnnotationServiceTestCase(unittest.TestCase):
    """Contract tests for the annotation stage.

    Annotation receives a stored image, runs object detection, and forwards the
    structured result to the document database service.
    """

    def setUp(self):
        self.module = load_module("app/services/annotation.py", "annotation_under_test")

    def test_annotation_service_contract_exposes_core_functions(self):
        # These function names define the intended public surface of the module.
        require_attr(self, self.module, "run_annotation")
        require_attr(self, self.module, "package_document_message")
        require_attr(self, self.module, "publish_document_message")
        require_attr(self, self.module, "handle_annotation_event")

    def test_document_message_contract(self):
        package_document_message = require_attr(self, self.module, "package_document_message")

        message = package_document_message(
            image_id="img-123",
            image_path="app/storage/image_db/img-123.png",
            objects=[
                {"label": "dog", "confidence": 0.98, "bbox": [0.1, 0.2, 0.4, 0.6]}
            ],
        )

        # This payload captures the persisted annotation record that should be
        # sent downstream.
        self.assertEqual(
            message,
            {
                "event_name": "store_annotation",
                "image_id": "img-123",
                "image_path": "app/storage/image_db/img-123.png",
                "objects": [
                    {"label": "dog", "confidence": 0.98, "bbox": [0.1, 0.2, 0.4, 0.6]}
                ],
                "review": {"status": "pending", "notes": ""},
            },
        )

    def test_publish_document_message_uses_document_db_channel(self):
        publish_document_message = require_attr(self, self.module, "publish_document_message")
        fake_client = MagicMock()

        with patch.object(self.module.redis, "Redis", return_value=fake_client):
            publish_document_message(
                {
                    "event_name": "store_annotation",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                    "objects": [],
                    "review": {"status": "pending", "notes": ""},
                }
            )

        # The annotation stage should publish directly to the document DB
        # service, not to the vector index or CLI.
        fake_client.publish.assert_called_once_with(
            "document_db_channel",
            json.dumps(
                {
                    "event_name": "store_annotation",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                    "objects": [],
                    "review": {"status": "pending", "notes": ""},
                }
            ),
        )

    def test_handle_annotation_event_runs_detector_and_forwards_result(self):
        handle_annotation_event = require_attr(self, self.module, "handle_annotation_event")

        request = {
            "event_name": "annotate_image",
            "image_id": "img-123",
            "stored_image_path": "app/storage/image_db/img-123.png",
        }
        objects = [{"label": "cat", "conf": 0.99, "bbox": [0, 0, 1, 1]}]

        with patch.object(self.module, "run_annotation", return_value=objects) as run_mock, patch.object(
            self.module, "publish_document_message"
        ) as publish_mock:
            handle_annotation_event(request)

        # This test defines the orchestration responsibility of the service:
        # consume one annotation event, run the model, and forward one result.
        run_mock.assert_called_once_with("app/storage/image_db/img-123.png")
        publish_mock.assert_called_once_with(
            {
                "event_name": "store_annotation",
                "image_id": "img-123",
                "image_path": "app/storage/image_db/img-123.png",
                "objects": objects,
                "review": {"status": "pending", "notes": ""},
            }
        )
