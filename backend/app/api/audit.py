from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.api.auth import require_roles
from app.api.decisions import _status_for
from app.db import get_session_factory
from app.models import (
    ClassificationDecision,
    Document,
    DocumentScan,
    GatewayTransmission,
    Job,
    OutboundApproval,
    Request as AnalysisRequest,
    SecurityFinding,
    User,
)
from app.policy import POLICY_VERSION


router = APIRouter(prefix="/requests", tags=["Audit"])


class AuditEventResponse(BaseModel):
    event_id: str
    event_type: str
    status: str
    actor: str
    actor_role: str
    timestamp: datetime
    description: str
    metadata: dict[str, str] | None = None


class AuditEvidenceResponse(BaseModel):
    file_name: str
    file_size: str
    file_hash: str
    file_type: str
    request_id: str
    job_id: str | None
    grade: str
    detection_type: str | None
    policy_version: str
    approval_status: str
    post_inspection_status: str | None
    incident_id: str | None


class AuditApprovalResponse(BaseModel):
    id: str
    action: str
    actor: dict[str, str]
    acted_at: datetime
    reason: str | None = None


class AuditRecordResponse(BaseModel):
    request_id: str
    job_id: str | None
    grade: str
    policy_version: str
    current_status: str
    created_at: datetime
    completed_at: datetime | None
    incident_id: str | None
    events: list[AuditEventResponse]
    evidence: AuditEvidenceResponse
    approval_history: list[AuditApprovalResponse]


def _event(
    request_id: int,
    suffix: str,
    event_type: str,
    status: str,
    timestamp: datetime,
    description: str,
    actor: str = "SYSTEM",
    actor_role: str = "SYSTEM",
    metadata: dict[str, str] | None = None,
) -> AuditEventResponse:
    return AuditEventResponse(
        event_id=f"request-{request_id}-{suffix}",
        event_type=event_type,
        status=status,
        actor=actor,
        actor_role=actor_role,
        timestamp=timestamp,
        description=description,
        metadata=metadata,
    )


def _find_request(db, request_id: int, tenant_id: int):
    return db.execute(
        select(AnalysisRequest, Job, Document)
        .outerjoin(Job, Job.request_id == AnalysisRequest.id)
        .join(Document, AnalysisRequest.document_id == Document.id)
        .where(
            AnalysisRequest.id == request_id,
            AnalysisRequest.tenant_id == tenant_id,
        )
    ).first()


def _audit_record(db, request_id: int, tenant_id: int) -> AuditRecordResponse:
    result = _find_request(db, request_id, tenant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="감사 요청을 찾을 수 없습니다.")

    request, job, document = result
    classification = db.scalar(
        select(ClassificationDecision)
        .where(
            ClassificationDecision.document_id == document.id,
            ClassificationDecision.tenant_id == tenant_id,
        )
        .order_by(desc(ClassificationDecision.created_at))
    )
    if classification is None:
        raise HTTPException(status_code=404, detail="최종 등급 결정이 없습니다.")

    transmission = db.scalar(
        select(GatewayTransmission)
        .where(
            GatewayTransmission.document_id == document.id,
            GatewayTransmission.tenant_id == tenant_id,
        )
        .order_by(desc(GatewayTransmission.created_at))
    )
    approval = None
    if transmission is not None:
        approval = db.scalar(
            select(OutboundApproval).where(
                OutboundApproval.gateway_transmission_id == transmission.id,
                OutboundApproval.tenant_id == tenant_id,
            )
        )

    scan = db.scalar(select(DocumentScan).where(DocumentScan.document_id == document.id))
    findings = []
    if scan is not None:
        findings = list(
            db.scalars(
                select(SecurityFinding).where(SecurityFinding.scan_id == scan.id)
            )
        )

    status = _status_for(classification.confirmed_grade, transmission, approval)
    policy_version = transmission.policy_version if transmission else POLICY_VERSION
    post_status = transmission.post_inspection_status if transmission else None
    events = [
        _event(
            request.id,
            "created",
            "REQUEST_CREATED",
            "RECEIVED",
            request.created_at,
            "Analysis request created.",
        )
    ]
    if document.status not in {"QUARANTINED", "REJECTED"}:
        events.append(
            _event(
                request.id,
                "validated",
                "FILE_VALIDATED",
                "VALIDATED",
                document.created_at,
                "Document metadata and hash validation completed.",
            )
        )
    if job is not None:
        events.append(
            _event(
                request.id,
                "started",
                "ANALYSIS_STARTED",
                job.status,
                job.created_at,
                "Analysis job created for the document.",
            )
        )
    events.append(
        _event(
            request.id,
            "decision",
            "DECISION_CREATED",
            classification.confirmed_grade,
            classification.created_at,
            "Final C/S/O classification was recorded.",
            metadata={"grade": classification.confirmed_grade},
        )
    )

    approval_user = None
    decided_user = None
    if approval is not None:
        approval_user = db.get(User, approval.requested_by)
        if approval.decided_by is not None:
            decided_user = db.get(User, approval.decided_by)
        events.append(
            _event(
                request.id,
                "approval-requested",
                "APPROVAL_REQUESTED",
                "WAITING_APPROVAL",
                approval.created_at,
                "Masked payload approval was requested.",
                actor=approval_user.display_name if approval_user else "SYSTEM",
                actor_role=approval_user.role if approval_user else "SYSTEM",
            )
        )
        if approval.status in {"APPROVED", "REJECTED"}:
            event_type = "APPROVED" if approval.status == "APPROVED" else "REJECTED"
            events.append(
                _event(
                    request.id,
                    approval.status.lower(),
                    event_type,
                    approval.status,
                    approval.decided_at or approval.created_at,
                    f"Approval request {approval.status.lower()}.",
                    actor=decided_user.display_name if decided_user else "SYSTEM",
                    actor_role=decided_user.role if decided_user else "SYSTEM",
                )
            )

    if transmission is not None:
        events.append(
            _event(
                request.id,
                "payload-validated",
                "PAYLOAD_VALIDATED",
                transmission.policy_decision,
                transmission.created_at,
                "Outbound payload was evaluated by the policy engine.",
                metadata={"policy_version": transmission.policy_version},
            )
        )
        if transmission.policy_decision in {"ALLOWED", "APPROVED"}:
            events.append(
                _event(
                    request.id,
                    "transmitted",
                    "AI_TRANSMITTED",
                    transmission.status,
                    transmission.created_at,
                    "Gateway transmission was recorded without original content.",
                )
            )
        if transmission.post_inspection_status is not None:
            events.append(
                _event(
                    request.id,
                    "post-inspection",
                    (
                        "POST_INSPECTION_VERIFIED"
                        if transmission.post_inspection_status == "PASSED"
                        else "POST_INSPECTION_BLOCKED"
                    ),
                    transmission.post_inspection_status,
                    transmission.created_at,
                    "Post-Inspector result was recorded.",
                )
            )

    if status == "BLOCKED":
        events.append(
            _event(
                request.id,
                "blocked",
                "ANALYSIS_BLOCKED",
                "BLOCKED",
                transmission.created_at if transmission else classification.created_at,
                "Processing was blocked by the security policy.",
            )
        )
    elif status in {"ALLOWED", "APPROVED"}:
        events.append(
            _event(
                request.id,
                "completed",
                "COMPLETED",
                "COMPLETED",
                transmission.created_at if transmission else classification.created_at,
                "The recorded processing flow completed.",
            )
        )

    events.sort(key=lambda item: item.timestamp)
    completed_at = events[-1].timestamp if status in {"BLOCKED", "ALLOWED", "APPROVED", "REJECTED"} else None
    approval_history: list[AuditApprovalResponse] = []
    if approval is not None and approval.status in {"APPROVED", "REJECTED"}:
        approval_history.append(
            AuditApprovalResponse(
                id=str(approval.id),
                action=approval.status,
                actor={
                    "user_id": str(approval.decided_by or "system"),
                    "display_name": decided_user.display_name if decided_user else "SYSTEM",
                    "role": decided_user.role if decided_user else "SYSTEM",
                },
                acted_at=approval.decided_at or approval.created_at,
                reason=approval.decision_comment,
            )
        )

    return AuditRecordResponse(
        request_id=str(request.id),
        job_id=str(job.id) if job is not None else None,
        grade=classification.confirmed_grade,
        policy_version=policy_version,
        current_status=status,
        created_at=request.created_at,
        completed_at=completed_at,
        incident_id=(f"INC-TRANSMISSION-{transmission.id}" if transmission and transmission.status == "FAILED" else None),
        events=events,
        evidence=AuditEvidenceResponse(
            file_name=document.original_filename,
            file_size=f"{document.size_bytes} bytes",
            file_hash=f"SHA-256: {document.sha256}",
            file_type=document.mime_type,
            request_id=str(request.id),
            job_id=str(job.id) if job is not None else None,
            grade=classification.confirmed_grade,
            detection_type=", ".join(sorted({finding.category for finding in findings})) or None,
            policy_version=policy_version,
            approval_status=status,
            post_inspection_status=post_status,
            incident_id=(f"INC-TRANSMISSION-{transmission.id}" if transmission and transmission.status == "FAILED" else None),
        ),
        approval_history=approval_history,
    )


@router.get(
    "/{request_id}/audit",
    response_model=AuditRecordResponse,
    summary="분석 요청 감사 기록 조회",
)
def get_audit(
    request_id: int,
    current_user: User = Depends(
        require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")
    ),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        return _audit_record(db, request_id, current_user.tenant_id)


@router.get(
    "/{request_id}/audit/evidence",
    response_model=AuditEvidenceResponse,
    summary="분석 요청 감사 증적 요약 조회",
)
def get_audit_evidence(
    request_id: int,
    current_user: User = Depends(
        require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")
    ),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        return _audit_record(db, request_id, current_user.tenant_id).evidence


@router.get(
    "/{request_id}/audit.pdf",
    response_class=Response,
    summary="분석 요청 메타데이터 감사 PDF 생성",
)
def generate_audit_pdf(
    request_id: int,
    current_user: User = Depends(
        require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")
    ),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        record = _audit_record(db, request_id, current_user.tenant_id)
    body = (
        "%PDF-1.4\n"
        "1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        "2 0 obj<< /Type /Pages /Kids[3 0 R] /Count 1 >>endobj\n"
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox[0 0 612 792] /Contents 4 0 R >>endobj\n"
        "4 0 obj<< /Length 83 >>stream\n"
        "BT /F1 12 Tf 72 720 Td (PASSBOX metadata-only audit report) Tj ET\n"
        "endstream\nendobj\ntrailer<< /Root 1 0 R >>\n%%EOF"
    ).encode("ascii")
    return Response(
        content=body,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="audit-{record.request_id}.pdf"'
        },
    )
