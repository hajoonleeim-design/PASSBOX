import json
import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import require_roles
from app.db import get_session_factory
from app.models import SecurityPolicy, SecurityPolicyHistory, User


router = APIRouter(prefix="/admin/policies", tags=["Admin Policies"])

SecurityGrade = Literal["C", "S", "O"]
PolicyStatus = Literal["DRAFT", "ACTIVE", "INACTIVE"]
Severity = Literal["LOW", "MEDIUM", "HIGH"]


class CsoRulePayload(BaseModel):
    rule_id: str
    rule_name: str
    detection_type: str
    grade: SecurityGrade
    enabled: bool
    description: str


class ApprovalPolicyPayload(BaseModel):
    s_grade_requires_approval: bool
    approver_roles: list[str]
    c_grade_approvable: bool
    o_grade_requires_approval: bool


class ModelAllowlistPayload(BaseModel):
    model_id: str
    model_name: str
    provider: str
    enabled: bool
    description: str


class RetentionPolicyPayload(BaseModel):
    audit_days: int = Field(ge=1, le=3650)
    evidence_days: int = Field(ge=1, le=3650)
    incident_days: int = Field(ge=1, le=3650)


class DetectionPatternPayload(BaseModel):
    pattern_id: str
    pattern_name: str
    detection_type: str
    enabled: bool
    severity: Severity
    description: str


class PolicyPayload(BaseModel):
    policy_id: str | None = None
    institution_id: str
    version: str
    status: PolicyStatus
    effective_at: datetime
    updated_at: datetime
    updated_by: str
    cso_rules: list[CsoRulePayload]
    approval_policy: ApprovalPolicyPayload
    model_allowlist: list[ModelAllowlistPayload]
    retention_policy: RetentionPolicyPayload
    detection_patterns: list[DetectionPatternPayload]


class UpdatePolicyRequest(BaseModel):
    policy: PolicyPayload
    change_reason: str = Field(min_length=1, max_length=2000)


class PolicyChangeHistoryResponse(BaseModel):
    history_id: str
    policy_id: str
    version_before: str
    version_after: str
    changed_by: str
    actor_role: str
    changed_at: datetime
    change_reason: str
    changed_fields: list[str]
    before_value: str
    after_value: str


DEFAULT_CSO_RULES = [
    {
        "rule_id": "rule-pii",
        "rule_name": "민감정보 형식",
        "detection_type": "개인정보",
        "grade": "S",
        "enabled": True,
        "description": "민감정보 형식이 확인되면 승인 대상으로 분류합니다.",
    },
    {
        "rule_id": "rule-credential",
        "rule_name": "인증정보 형식",
        "detection_type": "인증정보",
        "grade": "C",
        "enabled": True,
        "description": "인증정보 형식이 확인되면 외부 전송을 차단합니다.",
    },
    {
        "rule_id": "rule-general",
        "rule_name": "일반 문서",
        "detection_type": "일반",
        "grade": "O",
        "enabled": True,
        "description": "정책 검증을 완료한 일반 문서입니다.",
    },
]
DEFAULT_APPROVAL_POLICY = {
    "s_grade_requires_approval": True,
    "approver_roles": ["APPROVER", "ADMIN"],
    "c_grade_approvable": False,
    "o_grade_requires_approval": False,
}
DEFAULT_MODEL_ALLOWLIST = [
    {
        "model_id": "security-ai-01",
        "model_name": "Security-AI-01",
        "provider": "Local Gateway",
        "enabled": True,
        "description": "기관에서 허용한 안전한 내부 테스트 모델입니다.",
    },
    {
        "model_id": "external-model-x",
        "model_name": "External-Model-X",
        "provider": "External Provider",
        "enabled": False,
        "description": "관리자 승인 전에는 사용할 수 없습니다.",
    },
]
DEFAULT_RETENTION_POLICY = {"audit_days": 365, "evidence_days": 180, "incident_days": 730}
DEFAULT_DETECTION_PATTERNS = [
    {
        "pattern_id": "pattern-phone",
        "pattern_name": "연락처 형식",
        "detection_type": "개인정보",
        "enabled": True,
        "severity": "MEDIUM",
        "description": "전화번호 형식의 민감정보를 탐지합니다.",
    },
    {
        "pattern_id": "pattern-credential",
        "pattern_name": "인증정보 형식",
        "detection_type": "인증정보",
        "enabled": True,
        "severity": "HIGH",
        "description": "토큰·비밀번호 등 인증정보 형식을 탐지합니다.",
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _default_policy(current_user: User) -> SecurityPolicy:
    now = _now()
    return SecurityPolicy(
        tenant_id=current_user.tenant_id,
        version="LOCAL-TEMPLATE-v1",
        status="ACTIVE",
        effective_at=now,
        updated_at=now,
        updated_by=current_user.display_name,
        cso_rules=DEFAULT_CSO_RULES,
        approval_policy=DEFAULT_APPROVAL_POLICY,
        model_allowlist=DEFAULT_MODEL_ALLOWLIST,
        retention_policy=DEFAULT_RETENTION_POLICY,
        detection_patterns=DEFAULT_DETECTION_PATTERNS,
    )


def _snapshot(policy: SecurityPolicy) -> dict:
    return {
        "cso_rules": policy.cso_rules or [],
        "approval_policy": policy.approval_policy or {},
        "model_allowlist": policy.model_allowlist or [],
        "retention_policy": policy.retention_policy or {},
        "detection_patterns": policy.detection_patterns or [],
    }


def _payload_snapshot(payload: PolicyPayload) -> dict:
    return {
        "cso_rules": [item.model_dump() for item in payload.cso_rules],
        "approval_policy": payload.approval_policy.model_dump(),
        "model_allowlist": [item.model_dump() for item in payload.model_allowlist],
        "retention_policy": payload.retention_policy.model_dump(),
        "detection_patterns": [item.model_dump() for item in payload.detection_patterns],
    }


def _next_version(version: str) -> str:
    match = re.search(r"(.*?)(\d+)$", version)
    if match is None:
        return f"{version}-2"
    return f"{match.group(1)}{int(match.group(2)) + 1}"


def _get_policy(db, policy_id: str, current_user: User, create_if_missing: bool = False):
    if policy_id in {"current", "mock-current", "mock-history", "mock-old"}:
        policy = db.scalar(
            select(SecurityPolicy).where(SecurityPolicy.tenant_id == current_user.tenant_id)
        )
        if policy is None and create_if_missing:
            policy = _default_policy(current_user)
            db.add(policy)
            db.flush()
        return policy

    try:
        numeric_id = int(policy_id)
    except ValueError:
        numeric_id = 0
    return db.scalar(
        select(SecurityPolicy).where(
            SecurityPolicy.id == numeric_id,
            SecurityPolicy.tenant_id == current_user.tenant_id,
        )
    )


def _to_response(policy: SecurityPolicy) -> PolicyPayload:
    return PolicyPayload(
        policy_id=str(policy.id),
        institution_id=str(policy.tenant_id),
        version=policy.version,
        status=policy.status,
        effective_at=policy.effective_at,
        updated_at=policy.updated_at,
        updated_by=policy.updated_by,
        cso_rules=policy.cso_rules or [],
        approval_policy=policy.approval_policy or {},
        model_allowlist=policy.model_allowlist or [],
        retention_policy=policy.retention_policy or {},
        detection_patterns=policy.detection_patterns or [],
    )


def _history_response(history: SecurityPolicyHistory) -> PolicyChangeHistoryResponse:
    return PolicyChangeHistoryResponse(
        history_id=str(history.id),
        policy_id=str(history.policy_id),
        version_before=history.version_before,
        version_after=history.version_after,
        changed_by=history.changed_by,
        actor_role=history.actor_role,
        changed_at=history.changed_at,
        change_reason=history.change_reason,
        changed_fields=history.changed_fields or [],
        before_value=json.dumps(history.before_value or {}, ensure_ascii=False),
        after_value=json.dumps(history.after_value or {}, ensure_ascii=False),
    )


@router.get("/{policy_id}", response_model=PolicyPayload, summary="관리자 정책 조회")
def get_policy(
    policy_id: str,
    current_user: User = Depends(require_roles("ADMIN")),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        policy = _get_policy(db, policy_id, current_user, create_if_missing=True)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="정책을 찾을 수 없습니다.")
        db.commit()
        return _to_response(policy)


@router.get("/{policy_id}/history", response_model=list[PolicyChangeHistoryResponse], summary="정책 변경 이력 조회")
def get_policy_history(
    policy_id: str,
    current_user: User = Depends(require_roles("ADMIN")),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        policy = _get_policy(db, policy_id, current_user)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="정책을 찾을 수 없습니다.")
        histories = db.scalars(
            select(SecurityPolicyHistory)
            .where(SecurityPolicyHistory.policy_id == policy.id)
            .order_by(desc(SecurityPolicyHistory.changed_at), desc(SecurityPolicyHistory.id))
            .limit(100)
        ).all()
        return [_history_response(item) for item in histories]


@router.put("/{policy_id}", response_model=PolicyPayload, summary="관리자 정책 새 버전 저장")
def update_policy(
    policy_id: str,
    payload: UpdatePolicyRequest,
    current_user: User = Depends(require_roles("ADMIN")),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        policy = _get_policy(db, policy_id, current_user, create_if_missing=True)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="정책을 찾을 수 없습니다.")
        if payload.policy.institution_id != str(current_user.tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="다른 기관의 정책은 변경할 수 없습니다.")

        previous = _snapshot(policy)
        next_values = _payload_snapshot(payload.policy)
        changed_fields = [key for key in previous if previous[key] != next_values[key]]
        if not changed_fields:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NO_CHANGES")

        history = SecurityPolicyHistory(
            policy_id=policy.id,
            version_before=policy.version,
            version_after=_next_version(policy.version),
            changed_by=current_user.display_name,
            actor_role=current_user.role,
            changed_at=_now(),
            change_reason=payload.change_reason.strip(),
            changed_fields=changed_fields,
            before_value={key: previous[key] for key in changed_fields},
            after_value={key: next_values[key] for key in changed_fields},
        )
        policy.version = history.version_after
        policy.status = "ACTIVE"
        policy.updated_at = history.changed_at
        policy.updated_by = current_user.display_name
        policy.cso_rules = next_values["cso_rules"]
        policy.approval_policy = next_values["approval_policy"]
        policy.model_allowlist = next_values["model_allowlist"]
        policy.retention_policy = next_values["retention_policy"]
        policy.detection_patterns = next_values["detection_patterns"]
        db.add(history)
        db.commit()
        db.refresh(policy)
        return _to_response(policy)
