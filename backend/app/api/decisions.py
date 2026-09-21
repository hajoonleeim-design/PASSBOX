from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.api.auth import get_current_user
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


router = APIRouter(prefix="/requests", tags=["Decisions"])


class DetectionEvidenceResponse(BaseModel):
    type: str
    item: str
    policy: str
    description: str


class DecisionActorResponse(BaseModel):
    user_id: str
    display_name: str
    role: str


class ApprovalHistoryResponse(BaseModel):
    id: str
    action: str
    actor: DecisionActorResponse
    acted_at: datetime
    reason: str | None = None


class DecisionResponse(BaseModel):
    request_id: int
    job_id: int | None
    file_name: str
    grade: str
    grade_name: str
    description: str
    detections: list[DetectionEvidenceResponse]
    policy_version: str
    masking_preview: str | None
    block_reason: str | None
    status: str
    created_at: datetime
    decided_at: datetime
    approval_id: int | None
    history: list[ApprovalHistoryResponse]


def _grade_copy(grade: str) -> tuple[str, str]:
    if grade == "C":
        return "기밀", "보안 정책에 따라 외부 AI 전송이 차단됩니다."
    if grade == "S":
        return "민감", "마스킹과 승인 확인 후 외부 AI 전송을 진행할 수 있습니다."
    return "공개", "정책 검증을 통과한 문서로 외부 AI 전송이 가능합니다."


def _status_for(
    grade: str,
    transmission: GatewayTransmission | None,
    approval: OutboundApproval | None,
) -> str:
    if transmission is None:
        return "BLOCKED" if grade == "C" else "UNKNOWN"
    if transmission.status == "BLOCKED" or transmission.policy_decision in {
        "BLOCKED",
        "PROMPT_BLOCKED",
    }:
        return "BLOCKED"
    if transmission.status == "FAILED":
        return "FAILED"
    if approval is not None and approval.status == "PENDING":
        return "WAITING_APPROVAL"
    if approval is not None and approval.status == "REJECTED":
        return "REJECTED"
    if transmission.status == "COMPLETED":
        return "APPROVED" if approval is not None else "ALLOWED"
    return "WAITING_APPROVAL" if grade == "S" else "UNKNOWN"


def _actor(user: User | None) -> DecisionActorResponse:
    if user is None:
        return DecisionActorResponse(
            user_id="system",
            display_name="SYSTEM",
            role="SYSTEM",
        )
    return DecisionActorResponse(
        user_id=str(user.id),
        display_name=user.display_name,
        role=user.role,
    )


@router.get(
    "/{request_id}/decision",
    response_model=DecisionResponse,
    summary="분석 요청의 보안 결정 결과 조회",
)
def get_decision(
    request_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        result = db.execute(
            select(AnalysisRequest, Job, Document)
            .outerjoin(Job, Job.request_id == AnalysisRequest.id)
            .join(Document, AnalysisRequest.document_id == Document.id)
            .where(
                AnalysisRequest.id == request_id,
                AnalysisRequest.tenant_id == current_user.tenant_id,
            )
        ).first()
        if result is None:
            raise HTTPException(status_code=404, detail="분석 요청을 찾을 수 없습니다.")

        request, job, document = result
        classification = db.scalar(
            select(ClassificationDecision)
            .where(
                ClassificationDecision.document_id == document.id,
                ClassificationDecision.tenant_id == current_user.tenant_id,
            )
            .order_by(desc(ClassificationDecision.created_at))
        )
        if classification is None:
            raise HTTPException(status_code=404, detail="최종 등급 결정이 없습니다.")

        transmission = db.scalar(
            select(GatewayTransmission)
            .where(
                GatewayTransmission.document_id == document.id,
                GatewayTransmission.tenant_id == current_user.tenant_id,
            )
            .order_by(desc(GatewayTransmission.created_at))
        )
        approval = None
        if transmission is not None:
            approval = db.scalar(
                select(OutboundApproval).where(
                    OutboundApproval.gateway_transmission_id == transmission.id,
                    OutboundApproval.tenant_id == current_user.tenant_id,
                )
            )

        scan = db.scalar(
            select(DocumentScan).where(DocumentScan.document_id == document.id)
        )
        findings = []
        if scan is not None:
            findings = list(
                db.scalars(
                    select(SecurityFinding).where(SecurityFinding.scan_id == scan.id)
                )
            )

        actor_ids = {classification.user_id}
        if approval is not None:
            actor_ids.add(approval.requested_by)
            if approval.decided_by is not None:
                actor_ids.add(approval.decided_by)
        users = {
            user.id: user
            for user in db.scalars(select(User).where(User.id.in_(actor_ids))).all()
        }

        grade_name, description = _grade_copy(classification.confirmed_grade)
        policy_version = transmission.policy_version if transmission else POLICY_VERSION
        detections = [
            DetectionEvidenceResponse(
                type=finding.category,
                item=f"{finding.category} ({finding.match_count})",
                policy=policy_version,
                description=(
                    f"{finding.severity} severity finding recorded by the security scanner."
                ),
            )
            for finding in findings
        ]
        status = _status_for(classification.confirmed_grade, transmission, approval)
        history: list[ApprovalHistoryResponse] = []
        if approval is not None and approval.status in {"APPROVED", "REJECTED"}:
            decided_by = users.get(approval.decided_by or 0)
            history.append(
                ApprovalHistoryResponse(
                    id=str(approval.id),
                    action=approval.status,
                    actor=_actor(decided_by),
                    acted_at=approval.decided_at or approval.created_at,
                    reason=approval.decision_comment,
                )
            )

        block_reason = None
        if status == "BLOCKED":
            block_reason = (
                transmission.error_message
                if transmission is not None and transmission.error_message
                else "외부 AI 전송이 보안 정책에 의해 차단되었습니다."
            )

        masking_preview = None
        if approval is not None:
            categories = [
                item for item in (approval.masking_categories or "").split(",") if item
            ]
            if categories:
                masking_preview = (
                    f"민감정보 마스킹 완료: {', '.join(categories)} "
                    f"({approval.masking_version})"
                )

        decided_at = (
            transmission.created_at
            if transmission is not None
            else classification.created_at
        )
        return DecisionResponse(
            request_id=request.id,
            job_id=job.id if job is not None else None,
            file_name=document.original_filename,
            grade=classification.confirmed_grade,
            grade_name=grade_name,
            description=description,
            detections=detections,
            policy_version=policy_version,
            masking_preview=masking_preview,
            block_reason=block_reason,
            status=status,
            created_at=request.created_at,
            decided_at=decided_at,
            approval_id=approval.id if approval is not None else None,
            history=history,
        )
