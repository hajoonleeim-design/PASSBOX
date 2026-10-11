"""정책에 의한 O 등급 자동 확정(대량 처리용, 기본 꺼짐).

기본 흐름은 모든 문서를 담당자가 한 건씩 확정한다. 문서가 수백~수천 건이면 그 방식은 쓸 수 없으므로,
기관이 정책에서 직접 켠 경우에만 "위험이 거의 없는 O"를 정책이 대신 확정한다. 켜지 않으면 아무 일도 하지 않는다.

자동 확정은 아래를 모두 만족할 때만 한다. 하나라도 어긋나면 기존처럼 담당자 확정 대기로 남는다.
  1. 정책 approval_policy.o_grade_auto_confirm 이 켜져 있다.
  2. 최종 추천 등급이 O다(모델 추천에 비밀 표기·탐지 보정까지 끝난 뒤의 값).
  3. 모델 확신도가 정책 기준(o_auto_confirm_min_confidence, 기본 0.95) 이상이다.
  4. 보안 탐지 결과가 0건이다(심각도 낮은 탐지도 하나만 있으면 사람이 본다).
  5. 규칙 기반 임시 분류기가 아니라 실제 분류 모델의 추천이다.
S·C는 절대 자동 확정하지 않는다. 자동 확정은 감사 기록에 사람이 한 확정과 구분되는 이벤트로 남는다.
"""
from sqlalchemy import select

from app.audit_chain import append_audit_entry
from app.models import ClassificationDecision, ClassificationRecommendation, Document, SecurityFinding, User
from app.policy import get_active_policy_configuration

SYSTEM_USERNAME = "system.autoconfirm"
SYSTEM_DISPLAY_NAME = "정책 자동 확정"
DEFAULT_MIN_CONFIDENCE = 0.95


def get_or_create_system_user(db, tenant_id: int) -> User:
    """기관마다 하나, 로그인할 수 없는 시스템 계정. 확정자 칸에 '정책 자동 확정'으로 표시하기 위해 쓴다."""
    user = db.scalar(select(User).where(User.tenant_id == tenant_id, User.username == SYSTEM_USERNAME))
    if user is None:
        # password_hash가 비어 있고 상태가 DISABLED라 어떤 비밀번호로도 로그인할 수 없다.
        user = User(
            tenant_id=tenant_id,
            username=SYSTEM_USERNAME,
            display_name=SYSTEM_DISPLAY_NAME,
            password_hash="",
            role="SYSTEM",
            status="DISABLED",
        )
        db.add(user)
        db.flush()
    return user


def auto_confirm_decision_reason(
    *, approval_policy: dict, recommendation: ClassificationRecommendation, finding_count: int
) -> str | None:
    """자동 확정 조건을 모두 만족하면 None, 아니면 건너뛴 이유를 돌려준다(테스트·감사용)."""
    if not approval_policy.get("o_grade_auto_confirm", False):
        return "정책이 꺼져 있음"
    if recommendation.recommended_grade != "O":
        return "추천 등급이 O가 아님"
    threshold = float(approval_policy.get("o_auto_confirm_min_confidence", DEFAULT_MIN_CONFIDENCE))
    if recommendation.confidence is None or recommendation.confidence < threshold:
        return "모델 확신도가 기준 미만"
    if finding_count > 0:
        return "보안 탐지 결과가 있음"
    if str(recommendation.model_version or "").startswith("local-rules"):
        return "실제 분류 모델의 추천이 아님"
    return None


def maybe_auto_confirm(db, document: Document, recommendation: ClassificationRecommendation, scan_id: int) -> bool:
    """조건을 만족하면 O 확정 기록을 만들고 True를 돌려준다. 호출한 쪽이 커밋한다."""
    already = db.scalar(
        select(ClassificationDecision.id).where(
            ClassificationDecision.document_id == document.id,
            ClassificationDecision.tenant_id == document.tenant_id,
        )
    )
    if already is not None:
        return False

    policy = get_active_policy_configuration(db, document.tenant_id)
    finding_count = len(
        list(db.scalars(select(SecurityFinding.id).where(SecurityFinding.scan_id == scan_id)))
    )
    skip_reason = auto_confirm_decision_reason(
        approval_policy=policy.approval_policy, recommendation=recommendation, finding_count=finding_count
    )
    if skip_reason is not None:
        return False

    threshold = float(policy.approval_policy.get("o_auto_confirm_min_confidence", DEFAULT_MIN_CONFIDENCE))
    system_user = get_or_create_system_user(db, document.tenant_id)
    decision = ClassificationDecision(
        tenant_id=document.tenant_id,
        document_id=document.id,
        user_id=system_user.id,
        recommendation_id=recommendation.id,
        confirmed_grade="O",
        comment=(
            f"정책에 의한 자동 확정: 모델 O 추천(확신도 {recommendation.confidence:.2f} ≥ 기준 {threshold:.2f}), "
            "보안 탐지 0건, 비밀 표기 없음."
        ),
    )
    db.add(decision)
    db.flush()
    append_audit_entry(
        db,
        tenant_id=document.tenant_id,
        event_type="CLASSIFICATION_AUTO_CONFIRMED",
        payload={
            "document_id": document.id,
            "confirmed_grade": "O",
            "confirmed_by": system_user.id,
            "recommendation_id": recommendation.id,
            "confidence": recommendation.confidence,
            "min_confidence": threshold,
            "policy_version": policy.version,
            "automatic": True,
        },
    )
    document.status = "CLASSIFICATION_CONFIRMED"
    return True
