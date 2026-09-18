from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.models import SecurityPolicy


POLICY_VERSION = "LOCAL-TEMPLATE-v1"


@dataclass(frozen=True)
class PolicyConfiguration:
    version: str
    cso_rules: tuple[dict[str, Any], ...]
    approval_policy: dict[str, Any]
    model_allowlist: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class OutboundPolicyDecision:
    decision: str
    can_transmit: bool
    masking_required: bool
    reason: str


def default_policy_configuration() -> PolicyConfiguration:
    return PolicyConfiguration(
        version=POLICY_VERSION,
        cso_rules=(
            {"grade": "C", "enabled": True},
            {"grade": "S", "enabled": True},
            {"grade": "O", "enabled": True},
        ),
        approval_policy={
            "s_grade_requires_approval": True,
            "o_grade_requires_approval": False,
        },
        model_allowlist=(
            {"provider": "openai", "model_id": "gpt-4o-mini", "model_name": "gpt-4o-mini", "enabled": True},
            {"provider": "gemini", "model_id": "*", "model_name": "*", "enabled": True},
        ),
    )


def policy_configuration_from_record(policy: SecurityPolicy) -> PolicyConfiguration:
    return PolicyConfiguration(
        version=policy.version,
        cso_rules=tuple(policy.cso_rules or []),
        approval_policy=policy.approval_policy or {},
        model_allowlist=tuple(policy.model_allowlist or []),
    )


def get_active_policy_configuration(db, tenant_id: int) -> PolicyConfiguration:
    policy = db.scalar(
        select(SecurityPolicy).where(
            SecurityPolicy.tenant_id == tenant_id,
            SecurityPolicy.status == "ACTIVE",
        )
    )
    if policy is None:
        return default_policy_configuration()
    return policy_configuration_from_record(policy)


def _model_is_allowed(policy: PolicyConfiguration, provider: str, model: str) -> bool:
    normalized_provider = provider.strip().lower()
    normalized_model = model.strip().lower()
    for entry in policy.model_allowlist:
        if not entry.get("enabled"):
            continue
        entry_provider = str(entry.get("provider", "")).strip().lower()
        if entry_provider != normalized_provider:
            continue
        candidates = {
            str(entry.get("model_id", "")).strip().lower(),
            str(entry.get("model_name", "")).strip().lower(),
        }
        if "*" in candidates or normalized_model in candidates:
            return True
    return False


def _grade_is_enabled(policy: PolicyConfiguration, grade: str) -> bool:
    matching_rules = [rule for rule in policy.cso_rules if rule.get("grade") == grade]
    return any(bool(rule.get("enabled")) for rule in matching_rules)


def check_outbound_policy(
    *,
    confirmed_grade: str,
    provider: str,
    model: str,
    policy: PolicyConfiguration | None = None,
) -> OutboundPolicyDecision:
    active_policy = policy or default_policy_configuration()
    normalized_provider = provider.strip().lower()
    normalized_model = model.strip()
    if not normalized_model:
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="외부 AI model이 지정되지 않았습니다.",
        )
    if not _model_is_allowed(active_policy, normalized_provider, normalized_model):
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="현재 보안 정책의 provider/model 허용목록에 없습니다.",
        )

    if confirmed_grade not in {"C", "S", "O"} or not _grade_is_enabled(active_policy, confirmed_grade):
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="현재 보안 정책에서 유효하지 않거나 비활성화된 문서 등급입니다.",
        )
    if confirmed_grade == "C":
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="C등급 문서는 외부 AI로 전송할 수 없습니다.",
        )
    if confirmed_grade == "S" and active_policy.approval_policy.get("s_grade_requires_approval", True):
        return OutboundPolicyDecision(
            decision="APPROVAL_REQUIRED",
            can_transmit=False,
            masking_required=True,
            reason="S등급 문서는 민감정보를 마스킹한 뒤 담당자 승인이 필요합니다.",
        )
    if confirmed_grade == "S":
        return OutboundPolicyDecision(
            decision="ALLOWED",
            can_transmit=True,
            masking_required=True,
            reason="S등급 문서는 정책에 따라 마스킹 후 전송할 수 있습니다.",
        )
    if active_policy.approval_policy.get("o_grade_requires_approval", False):
        return OutboundPolicyDecision(
            decision="APPROVAL_REQUIRED",
            can_transmit=False,
            masking_required=False,
            reason="O등급 문서도 현재 정책에 따라 담당자 승인이 필요합니다.",
        )
    return OutboundPolicyDecision(
        decision="ALLOWED",
        can_transmit=True,
        masking_required=False,
        reason="O등급 문서이며 현재 정책의 provider/model 허용목록을 통과했습니다.",
    )
