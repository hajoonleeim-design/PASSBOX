from pathlib import Path

from sqlalchemy import select

from app.classifier import classifier
from app.db import Settings, get_session_factory
from app.extraction import UnsupportedDocumentError, extract_document
from app.models import (
    ClassificationDecision,
    ClassificationRecommendation,
    Document,
    DocumentScan,
    DocumentText,
    Job,
    Request as AnalysisRequest,
    SecurityFinding,
)
from app.security_scan import SCANNER_VERSION, scan_text


def _load_job(db, job_id: int, tenant_id: int):
    return db.execute(
        select(Job, AnalysisRequest, Document)
        .join(AnalysisRequest, Job.request_id == AnalysisRequest.id)
        .join(Document, AnalysisRequest.document_id == Document.id)
        .where(Job.id == job_id, AnalysisRequest.tenant_id == tenant_id)
    ).first()


def _set_job_state(
    db,
    job: Job,
    request: AnalysisRequest,
    *,
    status: str,
    progress: int,
    error_message: str | None = None,
) -> bool:
    if job.status == "CANCELLED":
        return False
    job.status = status
    job.progress = progress
    job.error_message = error_message
    request.status = status
    db.commit()
    db.refresh(job)
    return True


def _document_path(document: Document) -> Path:
    storage_root = Path(Settings().storage_root).resolve()
    storage_path = (storage_root / document.storage_key).resolve()
    if storage_root not in storage_path.parents or not storage_path.is_file():
        raise RuntimeError("격리 저장 파일을 찾을 수 없습니다.")
    return storage_path


def _save_extraction(db, document: Document, result) -> DocumentText:
    text_record = db.scalar(
        select(DocumentText).where(DocumentText.document_id == document.id)
    )
    result_status = "EXTRACTED_TRUNCATED" if result.truncated else "EXTRACTED"
    if text_record is None:
        text_record = DocumentText(
            tenant_id=document.tenant_id,
            document_id=document.id,
            extracted_text=result.text,
            extractor=result.extractor,
            char_count=len(result.text),
            truncated=result.truncated,
            status=result_status,
        )
        db.add(text_record)
    else:
        text_record.extracted_text = result.text
        text_record.extractor = result.extractor
        text_record.char_count = len(result.text)
        text_record.truncated = result.truncated
        text_record.status = result_status
    document.status = "TEXT_EXTRACTED"
    db.flush()
    return text_record


def _save_scan(db, document: Document, text_record: DocumentText) -> DocumentScan:
    existing = db.scalar(
        select(DocumentScan).where(DocumentScan.document_id == document.id)
    )
    if existing is not None:
        return existing

    findings = scan_text(text_record.extracted_text)
    high_count = sum(1 for finding in findings if finding.severity == "HIGH")
    scan = DocumentScan(
        tenant_id=document.tenant_id,
        document_id=document.id,
        status="SECURITY_REVIEW_REQUIRED" if high_count > 0 else "READY_FOR_CLASSIFICATION",
        total_findings=len(findings),
        high_severity_count=high_count,
        scanner_version=SCANNER_VERSION,
    )
    db.add(scan)
    db.flush()
    for finding in findings:
        db.add(
            SecurityFinding(
                scan_id=scan.id,
                tenant_id=document.tenant_id,
                document_id=document.id,
                category=finding.category,
                severity=finding.severity,
                match_count=finding.match_count,
                evidence_hash=finding.evidence_hash,
                line_hint=finding.line_hint,
            )
        )
    document.status = scan.status
    db.flush()
    return scan


def _save_recommendation(db, document: Document, scan: DocumentScan, text_record: DocumentText):
    existing = db.scalar(
        select(ClassificationRecommendation)
        .where(
            ClassificationRecommendation.document_id == document.id,
            ClassificationRecommendation.tenant_id == document.tenant_id,
        )
        .order_by(ClassificationRecommendation.created_at.desc())
    )
    if existing is not None:
        return existing

    findings = list(
        db.scalars(
            select(SecurityFinding).where(SecurityFinding.scan_id == scan.id)
        )
    )
    result = classifier.recommend(text_record.extracted_text, findings)
    recommendation = ClassificationRecommendation(
        tenant_id=document.tenant_id,
        document_id=document.id,
        recommended_grade=result.recommended_grade,
        confidence=result.confidence,
        reason=result.reason,
        model_version=result.model_version,
        status=result.status,
    )
    db.add(recommendation)
    document.status = "READY_FOR_CLASSIFICATION"
    db.flush()
    return recommendation


def process_document_job(job_id: int, tenant_id: int) -> None:
    """Run local extraction, security scanning, and provisional classification."""
    session_factory = get_session_factory()
    with session_factory() as db:
        result = _load_job(db, job_id, tenant_id)
        if result is None:
            return
        job, request, document = result
        if job.status != "QUEUED":
            return

        try:
            if not _set_job_state(db, job, request, status="INSPECTING", progress=10):
                return
            storage_path = _document_path(document)

            text_record = db.scalar(
                select(DocumentText).where(DocumentText.document_id == document.id)
            )
            if text_record is None or text_record.status not in {"EXTRACTED", "EXTRACTED_TRUNCATED"}:
                if not _set_job_state(db, job, request, status="PARSING", progress=30):
                    return
                extraction_result = extract_document(storage_path, document.extension)
                if not extraction_result.text:
                    raise RuntimeError("추출된 문서 텍스트가 없습니다.")
                text_record = _save_extraction(db, document, extraction_result)

            if not _set_job_state(db, job, request, status="DETECTING", progress=55):
                return
            scan = _save_scan(db, document, text_record)
            if scan.status != "READY_FOR_CLASSIFICATION":
                _set_job_state(
                    db,
                    job,
                    request,
                    status="BLOCKED",
                    progress=100,
                    error_message="보안 탐지 결과 담당자 검토가 필요합니다.",
                )
                return

            if not _set_job_state(db, job, request, status="CLASSIFICATION_REVIEW", progress=85):
                return
            _save_recommendation(db, document, scan, text_record)
            has_decision = db.scalar(
                select(ClassificationDecision.id).where(
                    ClassificationDecision.document_id == document.id,
                    ClassificationDecision.tenant_id == document.tenant_id,
                )
            )
            _set_job_state(
                db,
                job,
                request,
                status="COMPLETED" if has_decision is not None else "CLASSIFICATION_REVIEW",
                progress=100,
            )
        except UnsupportedDocumentError as exc:
            _set_job_state(db, job, request, status="FAILED", progress=100, error_message=str(exc))
        except Exception:
            _set_job_state(
                db,
                job,
                request,
                status="FAILED",
                progress=100,
                error_message="문서 분석 작업에 실패했습니다.",
            )
