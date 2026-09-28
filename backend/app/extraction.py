from dataclasses import dataclass
from html.parser import HTMLParser
import io
from pathlib import Path
from xml.etree import ElementTree
import zipfile

from docx import Document as WordDocument
from hwp5.dataio import ParseError as Hwp5ParseError
from hwp5.errors import InvalidHwp5FileError
from hwp5.hwp5odt import ODTTransform
from hwp5.xmlmodel import Hwp5File
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


MAX_EXTRACTED_CHARS = 2_000_000
TEXT_ENCODINGS = ("utf-8-sig", "cp949")


class UnsupportedDocumentError(Exception):
    pass


@dataclass
class ExtractionResult:
    text: str
    extractor: str
    truncated: bool


def extract_document(path: Path, extension: str) -> ExtractionResult:
    if extension in {".md", ".txt", ".csv"}:
        text = _extract_plain_text(path)
        extractor = "plain-text"
    elif extension in {".html", ".htm"}:
        text = _extract_html(path)
        extractor = "html-parser"
    elif extension == ".pdf":
        text = _extract_pdf(path)
        extractor = "pypdf"
    elif extension == ".hwpx":
        text = _extract_hwpx(path)
        extractor = "hwpx-xml"
    elif extension == ".pptx":
        text = _extract_pptx(path)
        extractor = "python-pptx"
    elif extension == ".xlsx":
        text = _extract_xlsx(path)
        extractor = "openpyxl"
    elif extension == ".docx":
        text = _extract_docx(path)
        extractor = "python-docx"
    elif extension == ".hwp":
        text = _extract_hwp(path)
        extractor = "pyhwp-odt"
    elif extension in {".ppt", ".xls", ".doc"}:
        raise UnsupportedDocumentError(
            "PPT/XLS/DOC 구형 바이너리 형식은 전용 파서 연결 후 지원할 수 있습니다."
        )
    else:
        raise UnsupportedDocumentError("지원하지 않는 문서 형식입니다.")

    normalized = _normalize_text(text)
    truncated = len(normalized) > MAX_EXTRACTED_CHARS
    if truncated:
        normalized = normalized[:MAX_EXTRACTED_CHARS]
    return ExtractionResult(
        text=normalized,
        extractor=extractor,
        truncated=truncated,
    )


def decode_plain_text(data: bytes) -> str:
    """Decode supported text-file encodings without silently replacing bytes."""
    encodings = list(TEXT_ENCODINGS)
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.insert(0, "utf-16")
    elif data and data.count(b"\x00") >= max(1, len(data) // 4):
        encodings.extend(("utf-16-le", "utf-16-be"))

    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    raise UnsupportedDocumentError("지원되는 텍스트 인코딩이 아닙니다.")


def _extract_plain_text(path: Path) -> str:
    return decode_plain_text(path.read_bytes())


class _HTMLTextExtractor(HTMLParser):
    """Collects visible text, skipping <script>/<style> content."""

    _SKIPPED_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _extract_html(path: Path) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(decode_plain_text(path.read_bytes()))
    parser.close()
    return parser.get_text()


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_hwpx(path: Path) -> str:
    sections: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        )
        for name in names:
            root = ElementTree.fromstring(archive.read(name))
            sections.append(" ".join(root.itertext()))
    return "\n".join(sections)


def _extract_pptx(path: Path) -> str:
    presentation = Presentation(str(path))
    slides: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        paragraphs: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                paragraphs.append(shape.text)
        slides.append(f"[슬라이드 {index}]\n" + "\n".join(paragraphs))
    return "\n".join(slides)


def _extract_docx(path: Path) -> str:
    document = WordDocument(str(path))
    parts: list[str] = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells if cell.text]
            if cells:
                parts.append("\t".join(cells))
    return "\n".join(parts)


def _extract_hwp(path: Path) -> str:
    """Extract text (including table cells) from a HWP v5 binary document.

    pyhwp only understands the HWP v5 container introduced with 한글 2002+;
    older HWP v3 files and DRM-encrypted documents raise here and are
    reported as unsupported rather than silently returning partial text.
    """
    try:
        hwp5file = Hwp5File(str(path))
    except (InvalidHwp5FileError, OSError) as exc:
        raise UnsupportedDocumentError(
            "지원되는 HWP(v5) 형식이 아니거나 파일을 열 수 없습니다."
        ) from exc

    try:
        content = io.BytesIO()
        ODTTransform().transform_hwp5_to_content(hwp5file, content)
    except Hwp5ParseError as exc:
        raise UnsupportedDocumentError("HWP 문서를 해석하지 못했습니다.") from exc
    finally:
        hwp5file.close()

    return odf_content_to_text(content.getvalue())


def odf_content_to_text(content_xml: bytes) -> str:
    """Flatten an ODF content.xml (paragraphs and table cells) into text."""
    root = ElementTree.fromstring(content_xml)
    return " ".join(part.strip() for part in root.itertext() if part.strip())


def _extract_xlsx(path: Path) -> str:
    # Quarantine files use the neutral `.upload` storage suffix. Passing the
    # path string makes openpyxl validate that suffix instead of the original
    # document extension, so provide a binary stream after the API has already
    # validated the upload signature and extension.
    with path.open("rb") as source:
        workbook = load_workbook(filename=source, read_only=True, data_only=True)
        try:
            sheets: list[str] = []
            for worksheet in workbook.worksheets:
                rows: list[str] = [f"[시트: {worksheet.title}]"]
                for row in worksheet.iter_rows(values_only=True):
                    values = [str(value) for value in row if value is not None]
                    if values:
                        rows.append("\t".join(values))
                sheets.append("\n".join(rows))
            return "\n".join(sheets)
        finally:
            workbook.close()


def _normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
