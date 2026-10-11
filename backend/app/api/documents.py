from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db import Settings, get_session_factory
from app.extraction import UnsupportedDocumentError, decode_plain_text
from app.access import document_access_clause
from app.models import Document, User
from app.antivirus import AntivirusUnavailable, scan_file
from app.security_scan import EICAR_TEST_SIGNATURE, contains_eicar_signature
from app.audit_chain import append_audit_entry


router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {
    ".hwpx", ".pdf", ".pptx", ".xlsx", ".docx",
    ".md", ".txt", ".csv", ".html",
}
TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".html"}
MAX_FILE_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: str


class InspectionResponse(BaseModel):
    document_id: int
    filename: str
    detected_format: str
    size_bytes: int
    sha256: str
    inspection_result: str
    status: str


def _expected_format(extension: str) -> tuple[str, ...]:
    if extension == ".pdf":
        return ("PDF",)
    if extension in {".hwpx", ".pptx", ".xlsx", ".docx"}:
        return ("ZIP",)
    if extension == ".hwp":
        return ("OLE",)
    if extension in TEXT_EXTENSIONS:
        return ("TEXT",)
    return ()


# Windows PE, Linux ELF, Mach-O (fat / 64-bit), shell script.
_EXECUTABLE_HEADERS = (bytes([0x4D, 0x5A]), bytes([0x7F, 0x45, 0x4C, 0x46]), bytes([0xCA, 0xFE, 0xBA, 0xBE]),
                       bytes([0xCF, 0xFA, 0xED, 0xFE]), b"#!")


def _detect_format(path: Path, extension: str | None = None) -> str:
    with path.open("rb") as source:
        header = source.read(8)

    # Executables renamed to an allowed extension (.exe -> .txt) are refused outright.
    if header.startswith(_EXECUTABLE_HEADERS):
        return "EXECUTABLE"
    if header.startswith(b"%PDF-"):
        return "PDF"
    if header.startswith(b"PK") and zipfile.is_zipfile(path):
        return "ZIP"
    if header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "OLE"
    if extension in TEXT_EXTENSIONS:
        try:
            decode_plain_text(path.read_bytes())
        except UnsupportedDocumentError:
            pass
        else:
            return "TEXT"
    return "UNKNOWN"


def _file_sha256_and_size(path: Path) -> tuple[str, int]:
    digest = sha256()
    size_bytes = 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
            size_bytes += len(chunk)
    return digest.hexdigest(), size_bytes


def _scan_for_eicar(path: Path) -> bool:
    """Chunked EICAR signature scan (see security_scan.py for what this
    does and does not prove). Keeps an overlap window between reads so the
    signature can't slip through by landing across a chunk boundary."""
    overlap = len(EICAR_TEST_SIGNATURE) - 1
    tail = b""
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            window = tail + chunk
            if contains_eicar_signature(window):
                return True
            tail = window[-overlap:]
    return False


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="문서 업로드",
    description=(
        "로그인한 사용자의 문서를 테넌트별 격리 저장소에 저장하고 DB에 기록합니다. "
        "이 단계에서는 파일을 분석하거나 외부 AI로 전송하지 않습니다."
    ),
)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    original_filename = Path(file.filename or "").name
    if not original_filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않은 파일 형식입니다. 허용 형식: {allowed}",
        )

    settings = Settings()
    storage_root = Path(settings.storage_root).resolve()
    quarantine_dir = storage_root / "quarantine" / str(current_user.tenant_id)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    storage_filename = f"{uuid4().hex}.upload"
    storage_path = quarantine_dir / storage_filename
    storage_key = str(storage_path.relative_to(storage_root)).replace("\\", "/")

    digest = sha256()
    size_bytes = 0

    try:
        with storage_path.open("wb") as output:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break

                size_bytes += len(chunk)
                if size_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="파일 크기는 50MB 이하만 업로드할 수 있습니다.",
                    )

                digest.update(chunk)
                output.write(chunk)

        session_factory = get_session_factory()
        with session_factory() as db:
            document = Document(
                tenant_id=current_user.tenant_id,
                uploaded_by=current_user.id,
                original_filename=original_filename,
                storage_key=storage_key,
                extension=extension,
                mime_type=file.content_type or "application/octet-stream",
                size_bytes=size_bytes,
                sha256=digest.hexdigest(),
                status="QUARANTINED",
            )
            db.add(document)
            db.flush()
            append_audit_entry(
                db,
                tenant_id=current_user.tenant_id,
                event_type="DOCUMENT_UPLOADED",
                payload={
                    "document_id": document.id,
                    "uploaded_by": current_user.id,
                    "sha256": document.sha256,
                    "size_bytes": document.size_bytes,
                    "extension": document.extension,
                },
            )
            db.commit()
            db.refresh(document)

            return UploadResponse(
                document_id=document.id,
                filename=document.original_filename,
                extension=document.extension,
                mime_type=document.mime_type,
                size_bytes=document.size_bytes,
                sha256=document.sha256,
                status=document.status,
            )
    except HTTPException:
        storage_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="파일 저장 중 오류가 발생했습니다.",
        ) from exc
    finally:
        file.file.close()


@router.post(
    "/{document_id}/inspect",
    response_model=InspectionResponse,
    summary="격리 문서 기본 안전성 검사",
    description=(
        "격리 저장된 파일의 확장자와 실제 파일 서명(Magic number), 크기, SHA-256을 확인하고, "
        "ClamAV 백신 엔진(clamd)으로 악성코드를 검사합니다. 실행 파일을 다른 확장자로 바꾼 "
        "파일은 거부하며, 검사 서버에 연결할 수 없으면(운영 모드) 통과시키지 않습니다. "
        "통과한 파일만 파싱 대기 상태로 바뀝니다."
    ),
)
def inspect_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        if document.status != "QUARANTINED":
            raise HTTPException(
                status_code=409,
                detail=f"검사할 수 없는 문서 상태입니다: {document.status}",
            )

        storage_root = Path(Settings().storage_root).resolve()
        storage_path = (storage_root / document.storage_key).resolve()
        if storage_root not in storage_path.parents:
            raise HTTPException(status_code=500, detail="잘못된 저장 경로입니다.")

        if not storage_path.is_file():
            document.status = "REJECTED"
            db.commit()
            raise HTTPException(status_code=422, detail="격리 저장 파일을 찾을 수 없습니다.")

        try:
            detected_format = _detect_format(storage_path, document.extension)
            actual_sha256, actual_size = _file_sha256_and_size(storage_path)
        except OSError:
            # The file exists but cannot be read: on a host with real-time antivirus this is
            # what a quarantined/locked malicious file looks like. Fail closed, not 500.
            document.status = "REJECTED"
            append_audit_entry(
                db,
                tenant_id=document.tenant_id,
                event_type="MALWARE_DETECTED",
                payload={"document_id": document.id, "engine": "host-antivirus", "signature": "file locked by host antivirus", "sha256": document.sha256},
            )
            db.commit()
            raise HTTPException(status_code=422, detail="서버 백신이 파일을 차단해 검사할 수 없습니다. 파일을 거부했습니다.")
        expected_formats = _expected_format(document.extension)

        if (
            detected_format not in expected_formats
            or actual_size != document.size_bytes
            or actual_sha256 != document.sha256
        ):
            document.status = "REJECTED"
            db.commit()
            raise HTTPException(
                status_code=422,
                detail="파일 형식 또는 무결성 검사에 실패했습니다.",
            )

        try:
            av = scan_file(storage_path)
        except AntivirusUnavailable as exc:
            # Fail closed: a file that could not be scanned stays quarantined.
            db.rollback()
            raise HTTPException(status_code=503, detail=f"{exc} 잠시 후 다시 검사해 주세요.") from exc
        if av.status == "INFECTED" or _scan_for_eicar(storage_path):
            document.status = "REJECTED"
            append_audit_entry(
                db,
                tenant_id=document.tenant_id,
                event_type="MALWARE_DETECTED",
                payload={"document_id": document.id, "engine": av.engine if av.status == "INFECTED" else "eicar-selftest",
                         "signature": av.signature or "Eicar-Test-Signature", "sha256": document.sha256},
            )
            db.commit()
            raise HTTPException(
                status_code=422,
                detail=f"악성코드가 탐지되어 파일을 거부했습니다 ({av.signature or 'EICAR 테스트 시그니처'}).",
            )

        document.status = "READY_FOR_PARSING"
        db.commit()

        return InspectionResponse(
            document_id=document.id,
            filename=document.original_filename,
            detected_format=detected_format,
            size_bytes=actual_size,
            sha256=actual_sha256,
            inspection_result="PASS",
            status=document.status,
        )
