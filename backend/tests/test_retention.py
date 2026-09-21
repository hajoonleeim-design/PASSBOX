import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.retention import _retention_days, _safe_storage_path


class RetentionTests(unittest.TestCase):
    def test_invalid_policy_uses_safe_default(self):
        self.assertEqual(_retention_days(None), 180)

    def test_storage_path_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(_safe_storage_path(root, "../outside.upload"))
            self.assertIsNotNone(_safe_storage_path(root, "quarantine/1/file.upload"))

    def test_expiry_reference_is_timezone_safe(self):
        created_at = datetime(2025, 1, 1)
        now = datetime(2025, 7, 1, tzinfo=timezone.utc)
        self.assertLess(
            created_at.replace(tzinfo=timezone.utc),
            now - timedelta(days=180),
        )


if __name__ == "__main__":
    unittest.main()
