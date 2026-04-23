from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests._helpers import load_module, require_attr


class CLITestCase(unittest.TestCase):
    """Contract tests for the user-facing CLI.

    The CLI is the only component a user talks to directly, so these tests
    describe both today's upload behavior and the future query behaviors the
    project is expected to expose.
    """

    def setUp(self):
        # Load the current top-level CLI entrypoint from disk for each test.
        self.cli = load_module("cli.py", "project_cli_under_test")

    def test_is_legal_path_accepts_supported_image_extensions_case_insensitively(self):
        is_legal_path = require_attr(self, self.cli, "is_legal_path")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Mixed-case suffix verifies that the validator treats image
            # extensions case-insensitively, which matters on Windows.
            image_path = Path(temp_dir) / "sample.JpG"
            image_path.write_bytes(b"fake image bytes")

            self.assertTrue(is_legal_path(str(image_path)))

    def test_is_legal_path_rejects_missing_file(self):
        is_legal_path = require_attr(self, self.cli, "is_legal_path")
        missing_path = Path(tempfile.gettempdir()) / "definitely_missing_image.png"
        self.assertFalse(is_legal_path(str(missing_path)))

    def test_is_legal_path_rejects_directory_and_unsupported_extension(self):
        is_legal_path = require_attr(self, self.cli, "is_legal_path")

        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            text_file = directory / "notes.txt"
            text_file.write_text("not an image", encoding="utf-8")

            self.assertFalse(is_legal_path(str(directory)))
            self.assertFalse(is_legal_path(str(text_file)))

    def test_package_upload_message_matches_upload_contract(self):
        package_upload_message = require_attr(self, self.cli, "package_upload_message")

        message = package_upload_message("C:/images/cat.png")

        # This payload is the CLI-to-image-uploader contract for the upload
        # user case.
        self.assertEqual(
            message,
            {
                "event_name": "upload_image",
                "image_path": "C:/images/cat.png",
            },
        )

    def test_publish_upload_message_uses_image_upload_channel(self):
        publish_upload_message = require_attr(self, self.cli, "publish_upload_message")
        fake_client = MagicMock()

        with patch.object(self.cli.redis, "Redis", return_value=fake_client):
            publish_upload_message({"event_name": "upload_image", "image_path": "a.png"})

        # The channel name is part of the system contract because downstream
        # services subscribe to it explicitly.
        fake_client.publish.assert_called_once_with(
            "image_upload_channel",
            json.dumps({"event_name": "upload_image", "image_path": "a.png"}),
        )

    def test_main_publishes_upload_request_after_valid_menu_flow(self):
        package_upload_message = require_attr(self, self.cli, "package_upload_message")

        with patch("builtins.input", side_effect=["1", "C:/images/cat.png", "4"]), patch.object(
            self.cli, "is_legal_path", return_value=True
        ), patch.object(
            self.cli, "package_upload_message", wraps=package_upload_message
        ) as package_mock, patch.object(
            self.cli, "publish_upload_message"
        ) as publish_mock:
            self.cli.main()

        # One successful upload interaction should build and publish exactly
        # one upload event before the user exits.
        package_mock.assert_called_once_with("C:/images/cat.png")
        publish_mock.assert_called_once()

    def test_main_publishes_topic_query_and_prints_results(self):
        package_topic_query_message = require_attr(self, self.cli, "package_topic_query_message")

        with patch("builtins.input", side_effect=["2", "sunset beach", "5", "4"]), patch.object(
            self.cli, "package_topic_query_message", wraps=package_topic_query_message
        ) as package_mock, patch.object(
            self.cli, "publish_query_message"
        ) as publish_mock, patch.object(
            self.cli,
            "listen_for_query_results",
            return_value={
                "event_name": "query_result",
                "source_event_name": "query_by_topic",
                "results": [],
            },
        ) as listen_mock, patch.object(
            self.cli, "print_query_results"
        ) as print_mock:
            self.cli.main()

        package_mock.assert_called_once_with("sunset beach", 5)
        publish_mock.assert_called_once()
        listen_mock.assert_called_once()
        print_mock.assert_called_once()

    def test_main_publishes_similarity_query_and_prints_results(self):
        package_similarity_query_message = require_attr(
            self, self.cli, "package_similarity_query_message"
        )

        with patch("builtins.input", side_effect=["3", "C:/images/query.png", "3", "4"]), patch.object(
            self.cli, "is_legal_path", return_value=True
        ), patch.object(
            self.cli, "package_similarity_query_message", wraps=package_similarity_query_message
        ) as package_mock, patch.object(
            self.cli, "publish_query_message"
        ) as publish_mock, patch.object(
            self.cli,
            "listen_for_query_results",
            return_value={
                "event_name": "query_result",
                "source_event_name": "query_similar_images",
                "results": [],
            },
        ) as listen_mock, patch.object(
            self.cli, "print_query_results"
        ) as print_mock:
            self.cli.main()

        package_mock.assert_called_once_with("C:/images/query.png", 3)
        publish_mock.assert_called_once()
        listen_mock.assert_called_once()
        print_mock.assert_called_once()

    def test_cli_contract_includes_topic_query_message_builder(self):
        # Future user case 2: user enters a text topic and requests matching
        # images from the vector index service.
        require_attr(self, self.cli, "package_topic_query_message")

    def test_cli_contract_includes_similarity_query_message_builder(self):
        # Future user case 3: user provides a query image and requests top-k
        # similar images from the vector index service.
        require_attr(self, self.cli, "package_similarity_query_message")

    def test_topic_query_message_contract(self):
        package_topic_query_message = require_attr(self, self.cli, "package_topic_query_message")

        message = package_topic_query_message("sunset beach", top_k=5)

        # This test locks down the expected payload for topic search so later
        # services can implement against a stable message shape.
        self.assertEqual(
            message,
            {
                "event_name": "query_by_topic",
                "topic": "sunset beach",
                "top_k": 5,
            },
        )

    def test_similarity_query_message_contract(self):
        package_similarity_query_message = require_attr(
            self, self.cli, "package_similarity_query_message"
        )

        message = package_similarity_query_message("C:/images/query.png", top_k=3)

        # This is the CLI contract for image-to-image retrieval.
        self.assertEqual(
            message,
            {
                "event_name": "query_similar_images",
                "image_path": "C:/images/query.png",
                "top_k": 3,
            },
        )
