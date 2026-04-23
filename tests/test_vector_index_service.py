from __future__ import annotations

import unittest
from unittest.mock import patch

from tests._helpers import load_module, require_attr


class VectorIndexServiceTestCase(unittest.TestCase):
    """Contract tests for the retrieval layer.

    The vector index has two roles: persist embeddings for later retrieval and
    answer topic-based or image-based nearest-neighbor queries.
    """

    def setUp(self):
        self.module = load_module(
            "app/services/vector_index_service.py", "vector_index_service_under_test"
        )

    def test_vector_index_service_contract_exposes_core_functions(self):
        # The retrieval layer needs both write-path and read-path functions.
        require_attr(self, self.module, "upsert_embedding")
        require_attr(self, self.module, "handle_index_event")
        require_attr(self, self.module, "encode_text_query")
        require_attr(self, self.module, "search_by_topic")
        require_attr(self, self.module, "search_by_similar_image")
        require_attr(self, self.module, "handle_topic_query_event")
        require_attr(self, self.module, "handle_similarity_query_event")

    def test_handle_index_event_stores_embedding_payload(self):
        handle_index_event = require_attr(self, self.module, "handle_index_event")

        with patch.object(self.module, "upsert_embedding") as upsert_mock:
            handle_index_event(
                {
                    "event_name": "index_embedding",
                    "image_id": "img-123",
                    "image_path": "app/storage/image_db/img-123.png",
                    "embedding": [0.1, 0.2, 0.3],
                }
            )

        # Index events should be reduced to vector + metadata storage.
        upsert_mock.assert_called_once_with(
            image_id="img-123",
            embedding=[0.1, 0.2, 0.3],
            metadata={"image_path": "app/storage/image_db/img-123.png"},
        )

    def test_handle_topic_query_event_embeds_text_and_returns_top_k_results(self):
        handle_topic_query_event = require_attr(self, self.module, "handle_topic_query_event")

        with patch.object(self.module, "encode_text_query", return_value=[0.4, 0.5, 0.6]) as encode_mock, patch.object(
            self.module, "search_by_topic", return_value=[{"image_id": "img-123", "score": 0.99}]
        ) as search_mock:
            results = handle_topic_query_event(
                {
                    "event_name": "query_by_topic",
                    "topic": "sunset beach",
                    "top_k": 5,
                }
            )

        # Topic search is a two-step operation: encode text, then search by
        # the resulting query vector.
        encode_mock.assert_called_once_with("sunset beach")
        search_mock.assert_called_once_with([0.4, 0.5, 0.6], top_k=5)
        self.assertEqual(results, [{"image_id": "img-123", "score": 0.99}])

    def test_handle_similarity_query_event_returns_top_k_similar_images(self):
        handle_similarity_query_event = require_attr(
            self, self.module, "handle_similarity_query_event"
        )

        with patch.object(
            self.module,
            "search_by_similar_image",
            return_value=[{"image_id": "img-234", "score": 0.97}],
        ) as search_mock:
            results = handle_similarity_query_event(
                {
                    "event_name": "query_similar_images",
                    "image_path": "C:/images/query.png",
                    "top_k": 3,
                }
            )

        # Image-to-image retrieval should expose a top-k result list just like
        # text search, but accept an image path instead of a topic string.
        search_mock.assert_called_once_with("C:/images/query.png", top_k=3)
        self.assertEqual(results, [{"image_id": "img-234", "score": 0.97}])
