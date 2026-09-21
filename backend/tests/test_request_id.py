import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import _resolve_request_id


class RequestIdTests(unittest.TestCase):
    def test_valid_client_request_id_is_preserved(self):
        self.assertEqual(_resolve_request_id("team-123.alpha"), "team-123.alpha")

    def test_missing_request_id_is_generated(self):
        with patch("app.main.uuid4", return_value=SimpleNamespace(hex="generated-id")):
            self.assertEqual(_resolve_request_id(None), "generated-id")

    def test_unsafe_request_id_is_replaced(self):
        with patch(
            "app.main.uuid4",
            return_value=SimpleNamespace(hex="safe-generated-id"),
        ):
            self.assertEqual(_resolve_request_id("bad\\r\\nvalue"), "safe-generated-id")


if __name__ == "__main__":
    unittest.main()
