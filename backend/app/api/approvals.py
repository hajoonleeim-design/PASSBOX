import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import get_current_user
from app.api.jobs import _update_latest_job_for_document
from app.db import get_session_factory
from app.gateway import GATEWAY_MODE, GatewayConfigurationError, gateway
from app.models import GatewayTransmission, OutboundApproval, User
from app.policy import get_active_policy_configuration
from app.post_inspector import inspect_response


router = APIRouter(prefix="/approvals", tags=["Approvals"])
APPROVAL_ROLES = ("APPROVER", "SECURITY_ADMIN", "ADMIN")


def _allowed_approval_roles(approval_policy: dict) -> set[str]:
    configured = {
        str(role).strip().upper()
        for role in approval_policy.get("approver_roles", [])
        if str(role).strip().upper() in APPROVAL_ROLES
    }
    if not configured:
        configured = {"APPROVER", "ADMIN"}
    # 보안 관리자는 정책 변경·사고 대응을 위한 비상 승인 권한을 유지합니다.
    configured.add("SECURITY_ADMIN")
    return configured


def require_approval_role(
    current_user: User = Depends(get_current_user),
) -> User:
    session_factory = get_session_factory()
    with session_factory() as db:
        policy = get_active_policy_configuration(db, current_user.tenant_id)
    if current_user.role not in _allowed_approval_roles(policy.approval_policy):
        raise HTTPException(
            status_code=403,
            detail="현재 보안 정책에서 승인 권한이 없는 사용자입니다.",
        )
    return current_user


class ApprovalDecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalResponse(BaseModel):
    approval_id: int
    document_id: int
    transmission_id: int
    provider: str
    model: str
    gateway_mode: str
    masking_version: str
    masking_categories: list[str]
    status: str
    transmission_status: str
    policy_decision: str
    post_inspection_status: str | None
    response: str | None
    requested_by: int
    decided_by: int | None
    decision_comment: str | None
    created_at: datetime
    decided_at: datetime | None


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _to_response(
    approval: OutboundApproval,
    transmission: GatewayTransmission,
    response: str | None = None,
) -> ApprovalResponse:
    categories = [
        item for item in (approval.masking_categories or "").split(",") if item
    ]
    return ApprovalResponse(
        approval_id=approval.id,
        document_id=approval.document_id,
        transmission_id=approval.gateway_transmission_id,
        provider=approval.provider,
        model=approval.model,
        gateway_mode=GATEWAY_MODE,
        masking_version=approval.masking_version,
        masking_categories=categories,
        status=approval.status,
        transmission_status=transmission.status,
        policy_decision=transmission.policy_decision,
        post_inspection_status=transmission.post_inspection_status,
        response=response,
        requested_by=approval.requested_by,
        decided_by=approval.decided_by,
        decision_comment=approval.decision_comment,
        created_at=approval.created_at,
        decided_at=approval.decided_at,
    )


def _get_approval(db, approval_id: int, tenant_id: int) -> OutboundApproval:
    approval = db.scalar(
        select(OutboundApproval).where(
            OutboundApproval.id == approval_id,
            OutboundApproval.tenant_id == tenant_id,
        ).with_for_update()
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="승인 요청을 찾을 수 없습니다.")
    return approval


def _get_transmission(db, approval: OutboundApproval) -> GatewayTransmission:
    transmission = db.scalar(
        select(GatewayTransmission).where(
            GatewayTransmission.id == approval.gateway_transmission_id,
            GatewayTransmission.tenant_id == approval.tenant_id,
        ).with_for_update()
    )
    if transmission is None:
        raise HTTPException(status_code=500, detail="Gateway 전송 감사 기록이 없습니다.")
    return transmission


def _prepare_gateway_attempt(
    db, approval: OutboundApproval, transmission: GatewayTransmission
) -> None:
    transmission.policy_decision = "APPROVED"
    transmission.status = "QUEUED"
    transmission.post_inspection_status = None
    transmission.response_hash = None
    transmission.response_categories = None
    transmission.error_message = None
    _update_latest_job_for_document(
        db,
        document_id=approval.document_id,
        tenant_id=approval.tenant_id,
        status_value="TRANSMITTING",
        progress=85,
        error_message=None,
    )
    db.commit()
    db.refresh(approval)
    db.refresh(transmission)


def _transmit_approved_payload(
    db,
    approval: OutboundApproval,
    transmission: GatewayTransmission,
    current_user: User,
) -> ApprovalResponse:
    try:
        gateway_response = gateway.send(
            provider=approval.provider,
            model=approval.model,
            prompt=approval.masked_payload,
            safety_identifier=_hash_text(
                f"{current_user.tenant_id}:{current_user.id}"
            ),
        )
        post_result = inspect_response(gateway_response.content)
        transmission.post_inspection_status = post_result.status
        transmission.response_categories = ",".join(post_result.categories)
        transmission.response_hash = _hash_text(gateway_response.content)
        transmission.status = (
            "COMPLETED" if post_result.status == "PASSED" else "BLOCKED"
        )
        transmission.error_message = (
            None
            if post_result.status == "PASSED"
            else "Post-Inspector blocked the response."
        )
        _update_latest_job_for_document(
            db,
            document_id=approval.document_id,
            tenant_id=approval.tenant_id,
            status_value="COMPLETED" if post_result.status == "PASSED" else "BLOCKED",
            progress=100,
            error_message=transmission.error_message,
        )
        db.commit()
        db.refresh(approval)
        db.refresh(transmission)
        return _to_response(
            approval,
            transmission,
            gateway_response.content if post_result.status == "PASSED" else None,
        )
    except GatewayConfigurationError as exc:
        transmission.status = "FAILED"
        transmission.error_message = str(exc)
        _update_latest_job_for_document(
            db,
            document_id=approval.document_id,
            tenant_id=approval.tenant_id,
            status_value="FAILED",
            progress=100,
            error_message=str(exc),
        )
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        transmission.status = "FAILED"
        transmission.error_message = "Gateway request failed."
        _update_latest_job_for_document(
            db,
            document_id=approval.document_id,
            tenant_id=approval.tenant_id,
            status_value="FAILED",
            progress=100,
            error_message="Gateway request failed.",
        )
        db.commit()
        raise HTTPException(status_code=502, detail="Gateway request failed.") from exc


@router.get(
    "/pending",
    response_model=list[ApprovalResponse],
    summary="대기 중인 S등급 승인 요청 조회",
)
def pending_approvals(
    current_user: User = Depends(require_approval_role),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        approvals = db.scalars(
            select(OutboundApproval)
            .where(
                OutboundApproval.tenant_id == current_user.tenant_id,
                OutboundApproval.status == "PENDING",
            )
            .order_by(desc(OutboundApproval.created_at))
        ).all()
        return [
            _to_response(approval, _get_transmission(db, approval))
            for approval in approvals
        ]


@router.get(
    "/retryable",
    response_model=list[ApprovalResponse],
    summary="Gateway 재시도 가능 승인 건 조회",
    description="승인은 완료되었지만 Gateway 전송에 실패한 건만 반환합니다.",
)
def retryable_approvals(
    current_user: User = Depends(require_approval_role),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        approvals = db.scalars(
            select(OutboundApproval)
            .join(
                GatewayTransmission,
                GatewayTransmission.id == OutboundApproval.gateway_transmission_id,
            )
            .where(
                OutboundApproval.tenant_id == current_user.tenant_id,
                OutboundApproval.status == "APPROVED",
                GatewayTransmission.status == "FAILED",
            )
            .order_by(desc(OutboundApproval.created_at))
        ).all()
        return [
            _to_response(approval, _get_transmission(db, approval))
            for approval in approvals
        ]


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalResponse,
    summary="S등급 요청 승인 후 마스킹 payload 전송",
)
def approve_request(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    current_user: User = Depends(require_approval_role),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        approval = _get_approval(db, approval_id, current_user.tenant_id)
        transmission = _get_transmission(db, approval)
        if approval.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="이미 처리된 승인 요청입니다.",
            )

        now = datetime.now(timezone.utc)
        approval.status = "APPROVED"
        approval.decided_by = current_user.id
        approval.decision_comment = payload.comment
        approval.decided_at = now
        transmission.policy_decision = "APPROVED"
        transmission.status = "QUEUED"
        transmission.error_message = None
        _update_latest_job_for_document(
            db,
            document_id=approval.document_id,
            tenant_id=approval.tenant_id,
            status_value="TRANSMITTING",
            progress=85,
            error_message=None,
        )
        db.commit()
        db.refresh(approval)
        db.refresh(transmission)

        try:
            gateway_response = gateway.send(
                provider=approval.provider,
                model=approval.model,
                prompt=approval.masked_payload,
                safety_identifier=_hash_text(
                    f"{current_user.tenant_id}:{current_user.id}"
                ),
            )
            post_result = inspect_response(gateway_response.content)
            transmission.post_inspection_status = post_result.status
            transmission.response_categories = ",".join(post_result.categories)
            transmission.response_hash = _hash_text(gateway_response.content)
            transmission.status = (
                "COMPLETED" if post_result.status == "PASSED" else "BLOCKED"
            )
            transmission.error_message = (
                None
                if post_result.status == "PASSED"
                else "Post-Inspector가 응답을 차단했습니다."
            )
            _update_latest_job_for_document(
                db,
                document_id=approval.document_id,
                tenant_id=approval.tenant_id,
                status_value="COMPLETED" if post_result.status == "PASSED" else "BLOCKED",
                progress=100,
                error_message=transmission.error_message,
            )
            db.commit()
            db.refresh(approval)
            db.refresh(transmission)
            return _to_response(
                approval,
                transmission,
                gateway_response.content if post_result.status == "PASSED" else None,
            )
        except GatewayConfigurationError as exc:
            transmission.status = "FAILED"
            transmission.error_message = str(exc)
            _update_latest_job_for_document(
                db,
                document_id=approval.document_id,
                tenant_id=approval.tenant_id,
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
                document_id=approval.document_id,
                tenant_id=approval.tenant_id,
                status_value="FAILED",
                progress=100,
                error_message="Gateway 호출에 실패했습니다.",
            )
            db.commit()
            raise HTTPException(status_code=502, detail="Gateway 호출에 실패했습니다.") from exc


@router.post(
    "/{approval_id}/retry",
    response_model=ApprovalResponse,
    summary="Gateway 전송 실패 승인 건 재시도",
    description="이미 승인되었지만 Gateway 호출에 실패한 건만 동일한 마스킹 Payload로 재전송합니다.",
)
def retry_approved_request(
    approval_id: int,
    current_user: User = Depends(require_approval_role),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        approval = _get_approval(db, approval_id, current_user.tenant_id)
        transmission = _get_transmission(db, approval)
        if approval.status != "APPROVED" or transmission.status != "FAILED":
            raise HTTPException(
                status_code=409,
                detail="Gateway 전송 실패 상태의 승인 건만 재시도할 수 있습니다.",
            )
        _prepare_gateway_attempt(db, approval, transmission)
        return _transmit_approved_payload(db, approval, transmission, current_user)


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalResponse,
    summary="S등급 Gateway 전송 승인 요청 반려",
)
def reject_request(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    current_user: User = Depends(require_approval_role),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        approval = _get_approval(db, approval_id, current_user.tenant_id)
        transmission = _get_transmission(db, approval)
        if approval.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="이미 처리된 승인 요청입니다.",
            )

        approval.status = "REJECTED"
        approval.decided_by = current_user.id
        approval.decision_comment = payload.comment
        approval.decided_at = datetime.now(timezone.utc)
        transmission.policy_decision = "REJECTED"
        transmission.status = "BLOCKED"
        transmission.error_message = payload.comment or "승인자가 전송을 반려했습니다."
        _update_latest_job_for_document(
            db,
            document_id=approval.document_id,
            tenant_id=approval.tenant_id,
            status_value="BLOCKED",
            progress=100,
            error_message=transmission.error_message,
        )
        db.commit()
        db.refresh(approval)
        db.refresh(transmission)
        return _to_response(approval, transmission)
