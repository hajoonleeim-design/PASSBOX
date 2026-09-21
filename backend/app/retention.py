from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.api.policies import DEFAULT_RETENTION_POLICY
from app.models import Document, SecurityPolicy


TERMINAL_DOCUMENT_STATUSES = frozenset({"CLASSIFICATION_CONFIRMED", "REJECTED"})


@dataclass(frozen=True)
class RetentionCandidate:
    document_id: int
    tenant_id: int
    storage_key: str
    path: Path
    created_at: datetime
    retention_days: int
    file_exists: bool


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _retention_days(policy: SecurityPolicy | None) -> int:
    configured = (policy.retention_policy or {}).get(
        "evidence_days", DEFAULT_RETENTION_POLICY["evidence_days"]
    ) if policy is not None else DEFAULT_RETENTION_POLICY["evidence_days"]
    try:
        days = int(configured)
    except (TypeError, ValueError):
        return DEFAULT_RETENTION_POLICY["evidence_days"]
    if not 1 <= days <= 3650:
        return DEFAULT_RETENTION_POLICY["evidence_days"]
    return days


def _safe_storage_path(storage_root: Path, storage_key: str) -> Path | None:
    root = storage_root.resolve()
    path = (root / storage_key).resolve()
    if path == root or root not in path.parents:
        return None
    return path


def list_storage_candidates(
    db,
    *,
    storage_root: Path,
    now: datetime | None = None,
) -> list[RetentionCandidate]:
    current_time = _utc(now or datetime.now(timezone.utc))
    result = db.execute(
        select(Document, SecurityPolicy)
        .outerjoin(SecurityPolicy, SecurityPolicy.tenant_id == Document.tenant_id)
        .where(Document.status.in_(TERMINAL_DOCUMENT_STATUSES))
        .order_by(Document.created_at)
    )

    candidates: list[RetentionCandidate] = []
    for document, policy in result.all():
        retention_days = _retention_days(policy)
        if _utc(document.created_at) >= current_time - timedelta(days=retention_days):
            continue

        path = _safe_storage_path(storage_root, document.storage_key)
        if path is None:
            continue
        candidates.append(
            RetentionCandidate(
                document_id=document.id,
                tenant_id=document.tenant_id,
                storage_key=document.storage_key,
                path=path,
                created_at=document.created_at,
                retention_days=retention_days,
                file_exists=path.is_file(),
            )
        )
    return candidates


def cleanup_storage(
    session_factory,
    *,
    storage_root: Path,
    apply: bool = False,
    now: datetime | None = None,
) -> dict:
    with session_factory() as db:
        candidates = list_storage_candidates(db, storage_root=storage_root, now=now)
        deleted_count = 0
        missing_count = 0
        if apply:
            for candidate in candidates:
                if not candidate.file_exists:
                    missing_count += 1
                    continue
                candidate.path.unlink()
                deleted_count += 1

    return {
        "dry_run": not apply,
        "candidate_count": len(candidates),
        "deleted_count": deleted_count,
        "missing_count": missing_count,
        "candidates": [
            {
                "document_id": candidate.document_id,
                "tenant_id": candidate.tenant_id,
                "storage_key": candidate.storage_key,
                "created_at": candidate.created_at.isoformat(),
                "retention_days": candidate.retention_days,
                "file_exists": candidate.file_exists,
            }
            for candidate in candidates
        ],
    }
