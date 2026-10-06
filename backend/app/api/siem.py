"""감사로그를 외부 보안관제센터(SIEM)로 내보내는 pull 방식 연동 지점.

PASSBOX는 자체 해시체인 감사로그를 갖고 있지만, 실제 공공기관 환경에서는
기관 보안관제센터(SOC)의 SIEM(Splunk 등)으로 로그를 모아 보는 경우가
많다. 지금은 이벤트를 밀어주는 webhook은 없고, SIEM이 주기적으로 당겨갈
수 있는 CEF(Common Event Format) pull 엔드포인트만 제공한다.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, select

from app.api.auth import require_roles
from app.db import get_session_factory
from app.models import AuditLogEntry, User


router = APIRouter(prefix="/audit", tags=["SIEM"])

# 1(정보)~10(긴급) 중 이벤트 성격에 맞춰 대략적인 CEF severity를 부여한다.
CEF_SEVERITY = {
    "PROMPT_INJECTION_DETECTED": 8,
    "MALICIOUS_LINK_DETECTED": 8,
    "APPROVAL_DECIDED": 5,
    "REVIEW_REQUEST_CREATED": 6,
    "REVIEW_REQUEST_DECIDED": 5,
    "CLASSIFICATION_CONFIRMED": 3,
}
DEFAULT_SEVERITY = 3


def _cef_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", " ").replace("|", "\\|")


def _to_cef_line(entry: AuditLogEntry) -> str:
    severity = CEF_SEVERITY.get(entry.event_type, DEFAULT_SEVERITY)
    created_at = entry.created_at if entry.created_at.tzinfo is not None else entry.created_at.replace(tzinfo=timezone.utc)
    extension = [
        f"rt={created_at.astimezone(timezone.utc).strftime('%b %d %Y %H:%M:%S')}",
        f"cs1Label=tenantId cs1={entry.tenant_id}",
        f"cs2Label=sequence cs2={entry.sequence}",
    ]
    if entry.request_id is not None:
        extension.append(f"cs3Label=requestId cs3={entry.request_id}")
    for key, value in sorted((entry.payload or {}).items()):
        safe_key = "".join(ch for ch in str(key) if ch.isalnum())[:20] or "field"
        extension.append(f"{safe_key}={_cef_escape(str(value))}")
    name = entry.event_type.replace("_", " ").title()
    return (
        f"CEF:0|PASSBOX|N2SF-AI-Gateway|1.0|{entry.event_type}|"
        f"{_cef_escape(name)}|{severity}|{' '.join(extension)}"
    )


@router.get(
    "/siem-export",
    summary="감사로그를 SIEM 연동용으로 내보내기 (CEF 또는 JSON)",
    description=(
        "SECURITY_ADMIN/ADMIN만 호출 가능. 기본은 CEF(Common Event Format) "
        "텍스트이며, format=json으로 원본 payload와 해시체인 필드를 그대로 받을 수 있습니다."
    ),
)
def export_siem(
    since: datetime | None = Query(default=None, description="이 시각 이후 기록만 (ISO 8601)"),
    until: datetime | None = Query(default=None, description="이 시각 이전 기록만 (ISO 8601)"),
    limit: int = Query(default=1000, ge=1, le=10000),
    export_format: str = Query(default="cef", alias="format", pattern="^(cef|json)$"),
    current_user: User = Depends(require_roles("SECURITY_ADMIN", "ADMIN")),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        conditions = [AuditLogEntry.tenant_id == current_user.tenant_id]
        if since is not None:
            conditions.append(AuditLogEntry.created_at >= since)
        if until is not None:
            conditions.append(AuditLogEntry.created_at <= until)
        entries = db.scalars(
            select(AuditLogEntry)
            .where(and_(*conditions))
            .order_by(AuditLogEntry.sequence)
            .limit(limit)
        ).all()

    if export_format == "json":
        return [
            {
                "sequence": entry.sequence,
                "event_type": entry.event_type,
                "request_id": entry.request_id,
                "created_at": entry.created_at.isoformat(),
                "payload": entry.payload,
                "record_hash": entry.record_hash,
                "previous_hash": entry.previous_hash,
            }
            for entry in entries
        ]

    body = "\n".join(_to_cef_line(entry) for entry in entries)
    return Response(content=body, media_type="text/plain")
