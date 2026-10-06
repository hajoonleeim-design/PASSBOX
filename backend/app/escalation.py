"""Shared helper for flagging stale items in a pending-review queue.

S등급 승인 대기(OutboundApproval)와 C등급 재검토 요청(ReviewRequest) 둘 다
"담당자가 확인해야 하는 대기열"이라는 점이 같아서, 일정 시간(기본 4시간,
Settings.escalation_hours로 조정) 넘게 PENDING 상태로 남아있으면 같은
기준으로 에스컬레이션 대상 표시를 한다. 실제 이메일/Slack 발송 채널은
아직 없고, 지금은 큐 화면에서 우선순위를 눈에 띄게 하는 것까지만 한다.
"""

from datetime import datetime, timezone

from app.db import Settings


def hours_pending(created_at: datetime, *, now: datetime | None = None) -> float:
    reference = now or datetime.now(timezone.utc)
    created = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
    return max(0.0, (reference - created).total_seconds() / 3600)


def is_escalated(created_at: datetime, *, now: datetime | None = None) -> bool:
    threshold = Settings().escalation_hours
    return hours_pending(created_at, now=now) >= threshold
