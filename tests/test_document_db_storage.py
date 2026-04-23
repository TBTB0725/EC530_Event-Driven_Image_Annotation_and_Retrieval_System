from __future__ import annotations

import unittest

from tests._helpers import load_module, require_attr


class _FakeCollection:
    """Tiny Mongo collection double that records upsert calls."""

    def __init__(self):
        self.calls = []

    def update_one(self, filter_query, update_payload, upsert=False):
        self.calls.append(
            {
                "filter_query": filter_query,
                "update_payload": update_payload,
                "upsert": upsert,
            }
        )


class DocumentDBStorageTestCase(unittest.TestCase):
    """Tests for the Mongo persistence helper layer."""

    def setUp(self):
        self.module = load_module("app/storage/document_db.py", "document_db_storage_under_test")

    def test_storage_contract_exposes_collection_and_upsert_helpers(self):
        require_attr(self, self.module, "create_client")
        require_attr(self, self.module, "get_collection")
        require_attr(self, self.module, "upsert_image_record")

    def test_upsert_image_record_uses_image_id_as_upsert_key(self):
        upsert_image_record = require_attr(self, self.module, "upsert_image_record")
        fake_collection = _FakeCollection()
        record = {
            "image_id": "img-123",
            "image_path": "app/storage/image_db/img-123.png",
            "objects": [{"label": "car", "conf": 0.93, "bbox": [1, 2, 3, 4]}],
            "review": {"status": "pending", "notes": ""},
        }

        stored_record = upsert_image_record(record, collection=fake_collection)

        self.assertEqual(stored_record, record)
        self.assertEqual(
            fake_collection.calls,
            [
                {
                    "filter_query": {"image_id": "img-123"},
                    "update_payload": {"$set": record},
                    "upsert": True,
                }
            ],
        )
