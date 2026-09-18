import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db import Settings, get_session_factory
from app.gateway import GatewayConfigurationError, gateway
from app.models import ChatRequest, User
from app.policy import check_outbound_policy, get_active_policy_configuration
from app.post_inspector import inspect_response
from app.security_scan import scan_text


router = APIRouter(prefix="/chat", tags=["AI Chat"])


class CreateChatRequestPayload(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)


class PostInspectionResponse(BaseModel):
    status: str
    inspected_at: datetime | None = None
    detection_type: str | None = None
    user_message: str
    incident_id: str | None = None


class ChatResponse(BaseModel):
    request_id: str
    model: str
    policy_version: str
    payload_status: str
    response_status: str
    decision_status: str
    post_inspection: PostInspectionResponse | None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    content: str | None = None


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_request_id(request_id: str) -> int:
    normalized = request_id.strip().upper()
    if normalized.startswith("CHAT-"):
        normalized = normalized[5:]
    try:
        parsed = int(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="AI 요청을 찾을 수 없습니다.") from exc
    if parsed <= 0:
        raise HTTPException(status_code=404, detail="AI 요청을 찾을 수 없습니다.")
    return parsed


def _incident_id(chat: ChatRequest) -> str:
    return f"INC-CHAT-{chat.id}"


def _post_inspection(chat: ChatRequest) -> PostInspectionResponse | None:
    status = chat.post_inspection_status
    if status is None:
        return None
    messages = {
        "PENDING": "AI 응답 검증을 기다리고 있습니다.",
        "INSPECTING": "AI 응답을 보안 검증하고 있습니다.",
        "VERIFIED": "AI 응답 보안 검증이 완료되었습니다.",
        "BLOCKED": "AI 응답이 보안 정책에 의해 차단되었습니다.",
        "FAILED": "AI 응답 검증에 실패했습니다. 안전을 위해 원문을 표시하지 않습니다.",
    }
    detection_type = "응답 보안 정책" if status in {"BLOCKED", "FAILED"} else None
    return PostInspectionResponse(
        status=status,
        inspected_at=chat.post_inspected_at,
        detection_type=detection_type,
        user_message=messages.get(status, "AI 응답 상태를 확인할 수 없습니다."),
        incident_id=chat.incident_id,
    )


def _to_response(chat: ChatRequest) -> ChatResponse:
    verified = (
        chat.response_status == "VERIFIED"
        and chat.post_inspection_status == "VERIFIED"
    )
    return ChatResponse(
        request_id=f"CHAT-{chat.id}",
        model=chat.model,
        policy_version=chat.policy_version,
        payload_status=chat.payload_status,
        response_status=chat.response_status,
        decision_status=chat.decision_status,
        post_inspection=_post_inspection(chat),
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        error_message=chat.error_message,
        content=chat.response_text if verified else None,
    )


def _finish_without_external_call(
    db,
    chat: ChatRequest,
    *,
    decision_status: str,
    reason: str,
    response_status: str = "BLOCKED",
) -> None:
    chat.payload_status = "BLOCKED"
    chat.response_status = response_status
    chat.decision_status = decision_status
    chat.post_inspection_status = "PENDING"
    chat.post_inspected_at = None
    chat.response_text = None
    chat.response_hash = None
    chat.response_categories = None
    chat.error_message = reason
    chat.incident_id = None
    chat.prompt_text = None
    chat.updated_at = _now()
    db.commit()
    db.refresh(chat)


def _process_chat(db, chat: ChatRequest, prompt: str) -> None:
    active_policy = get_active_policy_configuration(db, chat.tenant_id)
    chat.policy_version = active_policy.version
    findings = scan_text(prompt)
    if findings:
        categories = ", ".join(sorted({finding.category for finding in findings}))
        _finish_without_external_call(
            db,
            chat,
            decision_status="BLOCKED",
            reason=f"Prompt에서 보안 탐지 유형이 확인되어 외부 AI 전송을 차단했습니다: {categories}",
        )
        return

    policy_decision = check_outbound_policy(
        confirmed_grade="O",
        provider=chat.provider,
        model=chat.model,
        policy=active_policy,
    )
    if not policy_decision.can_transmit:
        _finish_without_external_call(
            db,
            chat,
            decision_status=(
                "WAITING_APPROVAL"
                if policy_decision.decision == "APPROVAL_REQUIRED"
                else "BLOCKED"
            ),
            reason=policy_decision.reason,
            response_status=(
                "NOT_RECEIVED"
                if policy_decision.decision == "APPROVAL_REQUIRED"
                else "BLOCKED"
            ),
        )
        return

    chat.payload_status = "VERIFIED"
    chat.response_status = "POST_INSPECTING"
    chat.decision_status = "ALLOWED"
    chat.post_inspection_status = "INSPECTING"
    chat.error_message = None
    chat.updated_at = _now()
    db.commit()
    db.refresh(chat)

    try:
        gateway_response = gateway.send(
            provider=chat.provider,
            model=chat.model,
            prompt=prompt,
            safety_identifier=_hash_text(f"{chat.tenant_id}:{chat.user_id}"),
        )
        post_result = inspect_response(gateway_response.content)
        chat.post_inspected_at = _now()
        chat.response_categories = ",".join(post_result.categories)
        chat.response_hash = _hash_text(gateway_response.content)
        if post_result.status == "PASSED":
            chat.response_status = "VERIFIED"
            chat.post_inspection_status = "VERIFIED"
            chat.response_text = gateway_response.content
            chat.error_message = None
            chat.incident_id = None
            chat.prompt_text = None
        else:
            chat.response_status = "BLOCKED"
            chat.post_inspection_status = "BLOCKED"
            chat.response_text = None
            chat.error_message = "Post-Inspector가 AI 응답을 차단했습니다."
            chat.incident_id = _incident_id(chat)
            chat.prompt_text = None
    except GatewayConfigurationError as exc:
        chat.response_status = "FAILED"
        chat.post_inspection_status = "FAILED"
        chat.error_message = str(exc)
        chat.incident_id = _incident_id(chat)
    except Exception:
        chat.response_status = "FAILED"
        chat.post_inspection_status = "FAILED"
        chat.error_message = "Gateway 호출에 실패했습니다."
        chat.incident_id = _incident_id(chat)
    finally:
        chat.updated_at = _now()
        db.commit()
        db.refresh(chat)


def _get_chat(db, request_id: str, tenant_id: int) -> ChatRequest:
    chat = db.scalar(
        select(ChatRequest).where(
            ChatRequest.id == _parse_request_id(request_id),
            ChatRequest.tenant_id == tenant_id,
        )
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="AI 요청을 찾을 수 없습니다.")
    return chat


@router.post("/requests", response_model=ChatResponse, summary="AI 채팅 요청 생성 및 안전 전송")
def create_chat_request(
    payload: CreateChatRequestPayload,
    current_user: User = Depends(get_current_user),
):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="질문을 입력해 주세요.")

    settings = Settings()
    model = settings.openai_model.strip() or "gpt-4o-mini"
    session_factory = get_session_factory()
    with session_factory() as db:
        policy = get_active_policy_configuration(db, current_user.tenant_id)
        chat = ChatRequest(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            provider="openai",
            model=model,
            policy_version=policy.version,
            prompt_hash=_hash_text(prompt),
            prompt_text=prompt,
            payload_status="VALIDATING",
            response_status="NOT_RECEIVED",
            decision_status="UNKNOWN",
            post_inspection_status="PENDING",
            error_message=None,
        )
        db.add(chat)
        db.flush()
        _process_chat(db, chat, prompt)
        return _to_response(chat)


@router.get("/requests/{request_id}", response_model=ChatResponse, summary="AI 채팅 요청 상태 조회")
def get_chat_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        return _to_response(_get_chat(db, request_id, current_user.tenant_id))


@router.post("/requests/{request_id}/send", response_model=ChatResponse, summary="AI 채팅 요청 전송")
def send_chat_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        chat = _get_chat(db, request_id, current_user.tenant_id)
        if not chat.prompt_text:
            return _to_response(chat)
        _process_chat(db, chat, chat.prompt_text)
        return _to_response(chat)


@router.get("/requests/{request_id}/post-inspection", response_model=PostInspectionResponse | None, summary="AI 응답 사후검사 상태 조회")
def get_chat_post_inspection(
    request_id: str,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        return _post_inspection(_get_chat(db, request_id, current_user.tenant_id))


@router.post("/requests/{request_id}/retry", response_model=ChatResponse, summary="실패한 AI 채팅 요청 재시도")
def retry_chat_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        chat = _get_chat(db, request_id, current_user.tenant_id)
        if not chat.prompt_text:
            raise HTTPException(
                status_code=409,
                detail="재시도할 안전한 Prompt가 보관되어 있지 않습니다. 새 요청을 생성해 주세요.",
            )
        prompt = chat.prompt_text
        chat.payload_status = "VALIDATING"
        chat.response_status = "NOT_RECEIVED"
        chat.decision_status = "UNKNOWN"
        chat.post_inspection_status = "PENDING"
        chat.post_inspected_at = None
        chat.response_text = None
        chat.response_hash = None
        chat.response_categories = None
        chat.error_message = None
        chat.incident_id = None
        chat.updated_at = _now()
        db.commit()
        db.refresh(chat)
        _process_chat(db, chat, prompt)
        return _to_response(chat)
