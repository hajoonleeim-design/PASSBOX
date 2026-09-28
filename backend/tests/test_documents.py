import tempfile
import unittest
from pathlib import Path

from app.api.documents import ALLOWED_EXTENSIONS, _detect_format, _expected_format


class DocumentFormatTests(unittest.TestCase):
    def test_markdown_and_text_are_allowed_text_formats(self):
        self.assertIn(".md", ALLOWED_EXTENSIONS)
        self.assertIn(".txt", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".md"), ("TEXT",))
        self.assertEqual(_expected_format(".txt"), ("TEXT",))

    def test_docx_is_an_allowed_zip_format(self):
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".docx"), ("ZIP",))

    def test_hwp_is_an_allowed_ole_format(self):
        self.assertIn(".hwp", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".hwp"), ("OLE",))

    def test_csv_and_html_are_allowed_text_formats(self):
        for extension in (".csv", ".html", ".htm"):
            self.assertIn(extension, ALLOWED_EXTENSIONS)
            self.assertEqual(_expected_format(extension), ("TEXT",))

    def test_utf8_text_is_detected_as_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.md"
            path.write_text("# 내부 공지\n외부 전송 전 검사가 필요합니다.", encoding="utf-8")

            self.assertEqual(_detect_format(path, ".md"), "TEXT")

    def test_binary_content_with_text_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.txt"
            path.write_bytes(b"\x00\x01\x02\xff\x00")

            self.assertEqual(_detect_format(path, ".txt"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
