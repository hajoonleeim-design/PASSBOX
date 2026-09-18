from dataclasses import dataclass


POLICY_VERSION = "LOCAL-TEMPLATE-v1"
ALLOWED_PROVIDERS = {"openai", "gemini"}


@dataclass(frozen=True)
class OutboundPolicyDecision:
    decision: str
    can_transmit: bool
    masking_required: bool
    reason: str


def check_outbound_policy(
    *, confirmed_grade: str, provider: str, model: str
) -> OutboundPolicyDecision:
    normalized_provider = provider.strip().lower()
    normalized_model = model.strip()
    if normalized_provider not in ALLOWED_PROVIDERS:
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="허용목록에 없는 외부 AI provider입니다.",
        )
    if not normalized_model:
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="외부 AI model이 지정되지 않았습니다.",
        )

    if confirmed_grade == "C":
        return OutboundPolicyDecision(
            decision="BLOCKED",
            can_transmit=False,
            masking_required=False,
            reason="C등급 문서는 외부 AI로 전송할 수 없습니다.",
        )
    if confirmed_grade == "S":
        return OutboundPolicyDecision(
            decision="APPROVAL_REQUIRED",
            can_transmit=False,
            masking_required=True,
            reason="S등급 문서는 민감정보를 마스킹한 뒤 담당자 승인이 필요합니다.",
        )
    return OutboundPolicyDecision(
        decision="ALLOWED",
        can_transmit=True,
        masking_required=False,
        reason="O등급 문서이며 허용된 provider/model에 대한 정책 재검사를 통과했습니다.",
    )
