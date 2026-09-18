from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db import get_session_factory
from app.models import Document, DocumentScan, DocumentText, SecurityFinding, User
from app.security_scan import SCANNER_VERSION, scan_text


router = APIRouter(prefix="/documents", tags=["Document Security Scan"])


class SecurityScanResponse(BaseModel):
    scan_id: int
    document_id: int
    status: str
    total_findings: int
    high_severity_count: int
    categories: list[str]
    classification_ready: bool
    created_at: datetime


def _to_response(scan: DocumentScan, findings: list[SecurityFinding]) -> SecurityScanResponse:
    categories = sorted({finding.category for finding in findings})
    return SecurityScanResponse(
        scan_id=scan.id,
        document_id=scan.document_id,
        status=scan.status,
        total_findings=scan.total_findings,
        high_severity_count=scan.high_severity_count,
        categories=categories,
        classification_ready=scan.status == "READY_FOR_CLASSIFICATION",
        created_at=scan.created_at,
    )


@router.post(
    "/{document_id}/scan",
    response_model=SecurityScanResponse,
    summary="개인정보·Secret·Prompt Injection 검사",
    description=(
        "추출된 텍스트를 규칙 기반으로 검사합니다. 민감한 원문은 저장하거나 응답하지 않고 "
        "탐지 유형·개수·해시만 기록합니다."
    ),
)
def scan_document(
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
            select(DocumentScan).where(DocumentScan.document_id == document.id)
        )
        if existing is not None:
            findings = list(
                db.scalars(
                    select(SecurityFinding).where(
                        SecurityFinding.scan_id == existing.id
                    )
                )
            )
            return _to_response(existing, findings)

        text_record = db.scalar(
            select(DocumentText).where(DocumentText.document_id == document.id)
        )
        if text_record is None or text_record.status not in {
            "EXTRACTED",
            "EXTRACTED_TRUNCATED",
        }:
            raise HTTPException(
                status_code=409,
                detail="먼저 텍스트 추출을 완료해야 보안 검사를 시작할 수 있습니다.",
            )

        findings = scan_text(text_record.extracted_text)
        high_count = sum(1 for finding in findings if finding.severity == "HIGH")
        scan_status = (
            "SECURITY_REVIEW_REQUIRED"
            if high_count > 0
            else "READY_FOR_CLASSIFICATION"
        )
        scan = DocumentScan(
            tenant_id=document.tenant_id,
            document_id=document.id,
            status=scan_status,
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

        document.status = scan_status
        db.commit()
        db.refresh(scan)
        saved_findings = list(
            db.scalars(
                select(SecurityFinding).where(SecurityFinding.scan_id == scan.id)
            )
        )
        return _to_response(scan, saved_findings)
