from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db import Settings, get_session_factory
from app.extraction import UnsupportedDocumentError, extract_document
from app.models import Document, DocumentText, User


router = APIRouter(prefix="/documents", tags=["Document Extraction"])


class ExtractionResponse(BaseModel):
    text_id: int
    document_id: int
    filename: str
    extractor: str
    char_count: int
    truncated: bool
    preview: str
    status: str


@router.post(
    "/{document_id}/extract",
    response_model=ExtractionResponse,
    summary="문서 텍스트 추출",
    description=(
        "안전성 검사를 통과한 문서에서 텍스트를 추출해 내부 DB에 저장합니다. "
        "추출 텍스트는 외부 AI로 전송하지 않습니다."
    ),
)
def extract_document_text(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        existing = db.scalar(
            select(DocumentText).where(DocumentText.document_id == document.id)
        )
        if existing is not None and existing.status in {"EXTRACTED", "EXTRACTED_TRUNCATED"}:
            return _to_response(existing, document)

        if document.status not in {"READY_FOR_PARSING", "TEXT_EXTRACTED"}:
            raise HTTPException(
                status_code=409,
                detail=f"텍스트를 추출할 수 없는 문서 상태입니다: {document.status}",
            )

        storage_root = Path(Settings().storage_root).resolve()
        storage_path = (storage_root / document.storage_key).resolve()
        if storage_root not in storage_path.parents:
            raise HTTPException(status_code=500, detail="잘못된 저장 경로입니다.")
        if not storage_path.is_file():
            raise HTTPException(status_code=422, detail="격리 저장 파일을 찾을 수 없습니다.")

        try:
            result = extract_document(storage_path, document.extension)
        except UnsupportedDocumentError as exc:
            _save_result(
                db=db,
                document=document,
                text="",
                extractor="unsupported",
                truncated=False,
                result_status="UNSUPPORTED",
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            _save_result(
                db=db,
                document=document,
                text="",
                extractor="error",
                truncated=False,
                result_status="FAILED",
            )
            raise HTTPException(status_code=422, detail="문서 텍스트 추출에 실패했습니다.") from exc

        if not result.text:
            _save_result(
                db=db,
                document=document,
                text="",
                extractor=result.extractor,
                truncated=result.truncated,
                result_status="EMPTY",
            )
            raise HTTPException(status_code=422, detail="추출된 텍스트가 없습니다.")

        result_status = "EXTRACTED_TRUNCATED" if result.truncated else "EXTRACTED"
        text_record = _save_result(
            db=db,
            document=document,
            text=result.text,
            extractor=result.extractor,
            truncated=result.truncated,
            result_status=result_status,
        )
        document.status = "TEXT_EXTRACTED"
        db.commit()
        db.refresh(text_record)
        return _to_response(text_record, document)


def _save_result(
    *, db, document: Document, text: str, extractor: str,
    truncated: bool, result_status: str,
) -> DocumentText:
    existing = db.scalar(
        select(DocumentText).where(DocumentText.document_id == document.id)
    )
    if existing is None:
        existing = DocumentText(
            tenant_id=document.tenant_id,
            document_id=document.id,
            extracted_text=text,
            extractor=extractor,
            char_count=len(text),
            truncated=truncated,
            status=result_status,
        )
        db.add(existing)
    else:
        existing.extracted_text = text
        existing.extractor = extractor
        existing.char_count = len(text)
        existing.truncated = truncated
        existing.status = result_status
    db.commit()
    db.refresh(existing)
    return existing


def _to_response(text_record: DocumentText, document: Document) -> ExtractionResponse:
    return ExtractionResponse(
        text_id=text_record.id,
        document_id=document.id,
        filename=document.original_filename,
        extractor=text_record.extractor,
        char_count=text_record.char_count,
        truncated=text_record.truncated,
        preview=text_record.extracted_text[:200],
        status=text_record.status,
    )
