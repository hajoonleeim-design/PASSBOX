import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.support import (
    SUPPORT_CONTENT,
    _parse_inquiry_id,
    _prepare_inquiry,
    _to_inquiry_response,
)


class SupportTests(unittest.TestCase):
    def test_support_content_is_available_from_backend_contract(self):
        self.assertGreater(len(SUPPORT_CONTENT.help), 0)
        self.assertGreater(len(SUPPORT_CONTENT.faqs), 0)
        self.assertIn("PDF", SUPPORT_CONTENT.file_formats)

    def test_inquiry_keeps_hash_and_non_sensitive_content_only(self):
        content_hash, masked_content = _prepare_inquiry("오류 문의", "오전 9시에 Job 상태가 멈췄습니다.")
        self.assertEqual(len(content_hash), 64)
        self.assertEqual(masked_content, "오전 9시에 Job 상태가 멈췄습니다.")

    def test_sensitive_inquiry_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            _prepare_inquiry("접속 문제", "password: do-not-store-this")
        self.assertEqual(context.exception.status_code, 422)

    def test_inquiry_id_parser_and_response_hide_internal_id(self):
        self.assertEqual(_parse_inquiry_id("INQ-20260918-0007"), 7)
        inquiry = SimpleNamespace(
            id=7,
            created_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
            category="ERROR",
            subject="Gateway 오류",
            status="RECEIVED",
            updated_at=datetime(2026, 9, 18, 0, 1, tzinfo=timezone.utc),
            masked_content="마스킹된 문의",
        )
        response = _to_inquiry_response(inquiry)
        self.assertEqual(response.inquiry_id, "INQ-20260918-0007")
        self.assertEqual(response.masked_content, "마스킹된 문의")
        self.assertNotIn("id", response.model_dump())


if __name__ == "__main__":
    unittest.main()
