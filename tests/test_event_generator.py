from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock

from tests._helpers import assert_has_event_metadata, load_module, require_attr


class EventGeneratorTestCase(unittest.TestCase):
    """Contract tests for the sample event generator utility.

    This module is used for service-isolated testing: a developer should be
    able to publish one stage's input event without running the whole pipeline.
    """

    def setUp(self):
        self.module = load_module(
            "app/services/event_generator.py", "event_generator_under_test"
        )

    def test_generator_exposes_builders_for_all_pipeline_events(self):
        require_attr(self, self.module, "build_upload_event")
        require_attr(self, self.module, "build_annotation_request_event")
        require_attr(self, self.module, "build_store_annotation_event")
        require_attr(self, self.module, "build_embed_image_event")
        require_attr(self, self.module, "build_index_embedding_event")
        require_attr(self, self.module, "build_topic_query_event")
        require_attr(self, self.module, "build_similarity_query_event")
        require_attr(self, self.module, "build_query_result_event")
        require_attr(self, self.module, "publish_sample_event")

    def test_build_sample_event_supports_every_event_name(self):
        build_sample_event = require_attr(self, self.module, "build_sample_event")

        supported_event_names = [
            "upload_image",
            "annotate_image",
            "store_annotation",
            "embed_image",
            "index_embedding",
            "query_by_topic",
            "query_similar_images",
            "query_result",
        ]

        for event_name in supported_event_names:
            with self.subTest(event_name=event_name):
                message = build_sample_event(event_name)
                self.assertEqual(message["event_name"], event_name)
                assert_has_event_metadata(self, message)

    def test_publish_sample_event_routes_upload_message_to_upload_channel(self):
        publish_sample_event = require_attr(self, self.module, "publish_sample_event")
        fake_client = MagicMock()

        channel, message = publish_sample_event(
            "upload_image",
            image_path="C:/images/cat.png",
            client=fake_client,
        )

        self.assertEqual(channel, "image_upload_channel")
        fake_client.publish.assert_called_once_with(
            "image_upload_channel",
            json.dumps(message),
        )

    def test_publish_sample_event_routes_document_event_to_document_channel(self):
        publish_sample_event = require_attr(self, self.module, "publish_sample_event")
        fake_client = MagicMock()

        channel, message = publish_sample_event(
            "store_annotation",
            image_id="img-123",
            image_path="app/storage/image_db/img-123.png",
            client=fake_client,
        )

        self.assertEqual(channel, "document_db_channel")
        fake_client.publish.assert_called_once_with(
            "document_db_channel",
            json.dumps(message),
        )
