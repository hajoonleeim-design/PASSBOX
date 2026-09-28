import tempfile
import unittest
from pathlib import Path

from docx import Document as WordDocument

from app.extraction import UnsupportedDocumentError, extract_document, odf_content_to_text


class TextExtractionTests(unittest.TestCase):
    def test_extracts_markdown_as_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.md"
            path.write_text("# 보안 정책\n\n외부 AI 전송 전 검사", encoding="utf-8")

            result = extract_document(path, ".md")

            self.assertEqual(result.extractor, "plain-text")
            self.assertIn("보안 정책", result.text)
            self.assertFalse(result.truncated)

    def test_extracts_cp949_text_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memo.txt"
            path.write_bytes("기관 내부 문서".encode("cp949"))

            result = extract_document(path, ".txt")

            self.assertEqual(result.text, "기관 내부 문서")

    def test_extracts_docx_paragraphs_and_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.docx"
            document = WordDocument()
            document.add_paragraph("외부 전송 전 보안 검사가 필요합니다.")
            table = document.add_table(rows=1, cols=2)
            table.rows[0].cells[0].text = "구분"
            table.rows[0].cells[1].text = "기밀"
            document.save(str(path))

            result = extract_document(path, ".docx")

            self.assertEqual(result.extractor, "python-docx")
            self.assertIn("외부 전송 전 보안 검사가 필요합니다.", result.text)
            self.assertIn("구분\t기밀", result.text)

    def test_hwp_with_invalid_container_is_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.hwp"
            path.write_bytes(b"not a real hwp file" * 10)

            with self.assertRaises(UnsupportedDocumentError):
                extract_document(path, ".hwp")

    def test_extracts_csv_as_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.csv"
            path.write_text("이름,등급\n기획서,S\n", encoding="utf-8")

            result = extract_document(path, ".csv")

            self.assertEqual(result.extractor, "plain-text")
            self.assertIn("기획서,S", result.text)

    def test_extracts_html_and_skips_script_and_style(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(
                "<html><head><style>body{color:red}</style></head>"
                "<body><h1>공지</h1><p>외부 전송 전 검사가 필요합니다.</p>"
                "<script>alert('should not appear')</script></body></html>",
                encoding="utf-8",
            )

            result = extract_document(path, ".html")

            self.assertEqual(result.extractor, "html-parser")
            self.assertIn("공지", result.text)
            self.assertIn("외부 전송 전 검사가 필요합니다.", result.text)
            self.assertNotIn("alert", result.text)
            self.assertNotIn("color:red", result.text)


class OdfContentTextTests(unittest.TestCase):
    def test_paragraphs_and_table_cells_are_flattened(self):
        content_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <office:document-content
            xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
            xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
            xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0">
          <office:body>
            <office:text>
              <text:p>외부 전송 전 검사가 필요합니다.</text:p>
              <table:table>
                <table:table-row>
                  <table:table-cell><text:p>구분</text:p></table:table-cell>
                  <table:table-cell><text:p>기밀</text:p></table:table-cell>
                </table:table-row>
              </table:table>
            </office:text>
          </office:body>
        </office:document-content>
        """.encode("utf-8")

        text = odf_content_to_text(content_xml)

        self.assertIn("외부 전송 전 검사가 필요합니다.", text)
        self.assertIn("구분", text)
        self.assertIn("기밀", text)


if __name__ == "__main__":
    unittest.main()
