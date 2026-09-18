from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import get_current_user
from app.db import get_session_factory
from app.models import (
    ClassificationDecision,
    Document,
    OutboundCheck,
    User,
)
from app.policy import POLICY_VERSION, check_outbound_policy


router = APIRouter(prefix="/documents", tags=["Outbound Policy Gate"])


class OutboundCheckRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)


class OutboundCheckResponse(BaseModel):
    check_id: int
    document_id: int
    provider: str
    model: str
    policy_version: str
    confirmed_grade: str
    decision: str
    can_transmit: bool
    masking_required: bool
    reason: str
    created_at: datetime


def _to_response(check: OutboundCheck) -> OutboundCheckResponse:
    return OutboundCheckResponse(
        check_id=check.id,
        document_id=check.document_id,
        provider=check.provider,
        model=check.model,
        policy_version=check.policy_version,
        confirmed_grade=check.confirmed_grade,
        decision=check.decision,
        can_transmit=check.can_transmit,
        masking_required=check.masking_required,
        reason=check.reason,
        created_at=check.created_at,
    )


@router.post(
    "/{document_id}/outbound/check",
    response_model=OutboundCheckResponse,
    summary="외부 AI 전송 정책 검사",
    description=(
        "실제 외부 전송 없이 확정 등급과 provider/model 허용목록을 검사합니다. "
        "이 API의 ALLOWED 결과가 있어야 이후 Gateway가 전송할 수 있습니다."
    ),
)
def check_outbound(
    document_id: int,
    payload: OutboundCheckRequest,
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

        decision = db.scalar(
            select(ClassificationDecision)
            .where(
                ClassificationDecision.document_id == document.id,
                ClassificationDecision.tenant_id == current_user.tenant_id,
            )
            .order_by(desc(ClassificationDecision.created_at))
        )
        if decision is None:
            raise HTTPException(
                status_code=409,
                detail="담당자가 C/S/O 등급을 최종 확정한 뒤 전송 검사를 요청해야 합니다.",
            )

        policy_decision = check_outbound_policy(
            confirmed_grade=decision.confirmed_grade,
            provider=payload.provider,
            model=payload.model,
        )
        check = OutboundCheck(
            tenant_id=document.tenant_id,
            document_id=document.id,
            user_id=current_user.id,
            provider=payload.provider.strip(),
            model=payload.model.strip(),
            policy_version=POLICY_VERSION,
            confirmed_grade=decision.confirmed_grade,
            decision=policy_decision.decision,
            can_transmit=policy_decision.can_transmit,
            masking_required=policy_decision.masking_required,
            reason=policy_decision.reason,
        )
        db.add(check)
        db.commit()
        db.refresh(check)
        return _to_response(check)
