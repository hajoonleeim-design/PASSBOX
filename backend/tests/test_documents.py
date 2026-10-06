import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.api.documents import ALLOWED_EXTENSIONS, _detect_format, _expected_format, _scan_for_eicar
from app.security_scan import EICAR_TEST_SIGNATURE


class DocumentFormatTests(unittest.TestCase):
    def test_markdown_and_text_are_allowed_text_formats(self):
        self.assertIn(".md", ALLOWED_EXTENSIONS)
        self.assertIn(".txt", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".md"), ("TEXT",))
        self.assertEqual(_expected_format(".txt"), ("TEXT",))

    def test_docx_is_an_allowed_zip_format(self):
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".docx"), ("ZIP",))

    def test_hwp_and_htm_are_no_longer_allowed(self):
        self.assertNotIn(".hwp", ALLOWED_EXTENSIONS)
        self.assertNotIn(".htm", ALLOWED_EXTENSIONS)

    def test_hwpx_is_an_allowed_zip_format(self):
        self.assertIn(".hwpx", ALLOWED_EXTENSIONS)
        self.assertEqual(_expected_format(".hwpx"), ("ZIP",))

    def test_csv_and_html_are_allowed_text_formats(self):
        for extension in (".csv", ".html"):
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


class EicarScanTests(unittest.TestCase):
    def test_clean_file_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.txt"
            path.write_text("평범한 공지 내용입니다.", encoding="utf-8")

            self.assertFalse(_scan_for_eicar(path))

    def test_eicar_test_file_is_detected(self):
        # A byte-for-byte standalone EICAR file trips the host machine's own
        # real-time antivirus before this test can even open it (which is,
        # amusingly, EICAR working as designed elsewhere). A small prefix
        # keeps this a test of OUR scanner, not of Windows Defender.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eicar.txt"
            path.write_bytes(b"test upload:\n" + EICAR_TEST_SIGNATURE)

            self.assertTrue(_scan_for_eicar(path))

    def test_signature_split_across_a_chunk_boundary_is_still_detected(self):
        """The overlap window must catch a signature straddling two reads,
        not just one that happens to land cleanly inside a single chunk."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eicar.txt"
            padding = b"x" * 100
            path.write_bytes(padding + EICAR_TEST_SIGNATURE + padding)

            with patch("app.api.documents.CHUNK_SIZE", 100 + 30):
                self.assertTrue(_scan_for_eicar(path))


if __name__ == "__main__":
    unittest.main()
