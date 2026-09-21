import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import get_current_user
from app.api.jobs import _update_latest_job_for_document
from app.db import get_session_factory
from app.gateway import GATEWAY_MODE, GatewayConfigurationError, gateway
from app.masking import MASKING_VERSION, mask_text
from app.models import (
    ClassificationDecision,
    Document,
    DocumentText,
    GatewayTransmission,
    OutboundApproval,
    User,
)
from app.policy import (
    OutboundPolicyDecision,
    check_outbound_policy,
    get_active_policy_configuration,
)
from app.post_inspector import inspect_response
from app.security_scan import scan_text


router = APIRouter(prefix="/documents", tags=["LLM Gateway"])

HARD_BLOCK_CATEGORIES = {
    "PROMPT_INJECTION",
    "PRIVATE_KEY",
    "API_KEY",
    "ACCESS_TOKEN",
    "SECRET",
}


class GatewayForwardRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    prompt: str | None = Field(default=None, max_length=10000)


class GatewayForwardResponse(BaseModel):
    transmission_id: int
    approval_id: int | None = None
    document_id: int
    provider: str
    model: str
    gateway_mode: str
    policy_version: str
    confirmed_grade: str
    policy_decision: str
    status: str
    post_inspection_status: str | None
    response: str | None
    response_hash: str | None
    response_categories: list[str]
    created_at: datetime


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _apply_prompt_policy(
    *,
    confirmed_grade: str,
    prompt_findings,
    policy_decision: OutboundPolicyDecision,
) -> OutboundPolicyDecision:
    """Apply payload-level security findings on top of the grade policy."""
    if not prompt_findings:
        return policy_decision

    finding_categories = {finding.category for finding in prompt_findings}
    if confirmed_grade == "S" and not finding_categories & HARD_BLOCK_CATEGORIES:
        return policy_decision

    return OutboundPolicyDecision(
        decision="PROMPT_BLOCKED",
        can_transmit=False,
        masking_required=False,
        reason="전송 payload에서 보안 탐지 유형이 확인되었습니다: "
        + ", ".join(sorted(finding_categories)),
    )


def _to_response(
    transmission: GatewayTransmission,
    response: str | None,
    approval_id: int | None = None,
) -> GatewayForwardResponse:
    categories = [
        item for item in (transmission.response_categories or "").split(",") if item
    ]
    return GatewayForwardResponse(
        transmission_id=transmission.id,
        approval_id=approval_id,
        document_id=transmission.document_id,
        provider=transmission.provider,
        model=transmission.model,
        gateway_mode=GATEWAY_MODE,
        policy_version=transmission.policy_version,
        confirmed_grade=transmission.confirmed_grade,
        policy_decision=transmission.policy_decision,
        status=transmission.status,
        post_inspection_status=transmission.post_inspection_status,
        response=response,
        response_hash=transmission.response_hash,
        response_categories=categories,
        created_at=transmission.created_at,
    )


@router.post(
    "/{document_id}/gateway/forward",
    response_model=GatewayForwardResponse,
    summary="정책 통과 문서의 LLM Gateway 전달",
    description=(
        "확정 등급과 전송 정책을 검사한 후 Gateway를 호출하고, AI 답변을 Post-Inspector로 "
        "재검사합니다. OPENAI 모드에서는 서버의 OPENAI_API_KEY만 사용하며, 키가 없으면 전송하지 않습니다."
    ),
)
def forward_to_gateway(
    document_id: int,
    payload: GatewayForwardRequest,
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

        classification = db.scalar(
            select(ClassificationDecision)
            .where(
                ClassificationDecision.document_id == document.id,
                ClassificationDecision.tenant_id == current_user.tenant_id,
            )
            .order_by(desc(ClassificationDecision.created_at))
        )
        if classification is None:
            raise HTTPException(
                status_code=409,
                detail="담당자가 C/S/O 등급을 최종 확정한 뒤 Gateway를 호출해야 합니다.",
            )

        text_record = db.scalar(
            select(DocumentText).where(DocumentText.document_id == document.id)
        )
        if text_record is None or text_record.status not in {
            "EXTRACTED",
            "EXTRACTED_TRUNCATED",
        }:
            raise HTTPException(status_code=409, detail="Gateway 호출 전에 문서 텍스트가 필요합니다.")

        prompt = payload.prompt.strip() if payload.prompt else text_record.extracted_text
        if not prompt:
            raise HTTPException(status_code=422, detail="Gateway에 전달할 텍스트가 없습니다.")

        active_policy = get_active_policy_configuration(db, current_user.tenant_id)
        policy_decision = check_outbound_policy(
            confirmed_grade=classification.confirmed_grade,
            provider=payload.provider,
            model=payload.model,
            policy=active_policy,
        )
        prompt_findings = scan_text(prompt)
        policy_decision = _apply_prompt_policy(
            confirmed_grade=classification.confirmed_grade,
            prompt_findings=prompt_findings,
            policy_decision=policy_decision,
        )
        gateway_prompt = prompt
        if policy_decision.decision == "ALLOWED" and policy_decision.masking_required:
            gateway_prompt = mask_text(prompt).masked_text
        transmission = GatewayTransmission(
            tenant_id=document.tenant_id,
            document_id=document.id,
            user_id=current_user.id,
            provider=payload.provider.strip(),
            model=payload.model.strip(),
            payload_hash=_hash_text(prompt),
            policy_version=active_policy.version,
            confirmed_grade=classification.confirmed_grade,
            policy_decision=policy_decision.decision,
            status=(
                "BLOCKED"
                if policy_decision.decision in {"BLOCKED", "PROMPT_BLOCKED"}
                else "WAITING_APPROVAL"
                if policy_decision.decision == "APPROVAL_REQUIRED"
                else "QUEUED"
            ),
            post_inspection_status=None,
            response_hash=None,
            response_categories=None,
            error_message=policy_decision.reason,
        )
        db.add(transmission)
        db.flush()

        if policy_decision.decision in {"BLOCKED", "PROMPT_BLOCKED"}:
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="BLOCKED",
                progress=100,
                error_message=policy_decision.reason,
            )
        elif policy_decision.decision == "APPROVAL_REQUIRED":
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="WAITING_APPROVAL",
                progress=70,
                error_message=policy_decision.reason,
            )
        else:
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="TRANSMITTING",
                progress=85,
                error_message=None,
            )

        if policy_decision.decision == "APPROVAL_REQUIRED":
            masking = mask_text(prompt)
            approval = OutboundApproval(
                tenant_id=document.tenant_id,
                document_id=document.id,
                requested_by=current_user.id,
                gateway_transmission_id=transmission.id,
                provider=payload.provider.strip(),
                model=payload.model.strip(),
                payload_hash=_hash_text(prompt),
                masked_payload_hash=_hash_text(masking.masked_text),
                masked_payload=masking.masked_text,
                masking_version=MASKING_VERSION,
                masking_categories=",".join(masking.categories),
                status="PENDING",
            )
            db.add(approval)
            db.commit()
            db.refresh(transmission)
            db.refresh(approval)
            return _to_response(transmission, None, approval.id)

        if not policy_decision.can_transmit:
            db.commit()
            db.refresh(transmission)
            return _to_response(transmission, None)

        try:
            gateway_response = gateway.send(
                provider=payload.provider.strip(),
                model=payload.model.strip(),
                prompt=gateway_prompt,
                safety_identifier=hashlib.sha256(
                    f"{current_user.tenant_id}:{current_user.id}".encode("utf-8")
                ).hexdigest(),
            )
            post_result = inspect_response(gateway_response.content)
            transmission.post_inspection_status = post_result.status
            transmission.response_categories = ",".join(post_result.categories)
            transmission.response_hash = _hash_text(gateway_response.content)
            transmission.status = "COMPLETED" if post_result.status == "PASSED" else "BLOCKED"
            transmission.error_message = None if post_result.status == "PASSED" else "Post-Inspector가 답변을 차단했습니다."
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="COMPLETED" if post_result.status == "PASSED" else "BLOCKED",
                progress=100,
                error_message=transmission.error_message,
            )
            db.commit()
            db.refresh(transmission)
            return _to_response(
                transmission,
                gateway_response.content if post_result.status == "PASSED" else None,
            )
        except GatewayConfigurationError as exc:
            transmission.status = "FAILED"
            transmission.error_message = str(exc)
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="FAILED",
                progress=100,
                error_message=str(exc),
            )
            db.commit()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            transmission.status = "FAILED"
            transmission.error_message = "Gateway 호출에 실패했습니다."
            _update_latest_job_for_document(
                db,
                document_id=document.id,
                tenant_id=document.tenant_id,
                status_value="FAILED",
                progress=100,
                error_message="Gateway 호출에 실패했습니다.",
            )
            db.commit()
            raise HTTPException(status_code=502, detail="Gateway 호출에 실패했습니다.") from exc
