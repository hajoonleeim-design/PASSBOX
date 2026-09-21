from io import BytesIO
from types import SimpleNamespace
import unittest

from pypdf import PdfReader

from app.api.audit import _build_audit_pdf, _pdf_escape


class AuditPdfTests(unittest.TestCase):
    def test_pdf_is_valid_and_contains_metadata_only_summary(self):
        record = SimpleNamespace(
            request_id="9",
            current_status="APPROVED",
            grade="S",
            policy_version="LOCAL-TEMPLATE-v1",
            events=[object(), object(), object()],
        )

        pdf = _build_audit_pdf(record)
        reader = PdfReader(BytesIO(pdf))
        text = reader.pages[0].extract_text()

        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Request ID: 9", text)
        self.assertIn("Current status: APPROVED", text)
        self.assertIn("Confirmed grade: S", text)
        self.assertIn("LOCAL-TEMPLATE-v1", text)
        self.assertIn("Original document and AI response are not included.", text)

    def test_pdf_escape_protects_pdf_string_delimiters(self):
        self.assertEqual(_pdf_escape(r"a\\b(c)"), r"a\\\\b\(c\)")


if __name__ == "__main__":
    unittest.main()
