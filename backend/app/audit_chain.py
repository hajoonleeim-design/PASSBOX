"""Tamper-evident audit log: a per-tenant hash chain.

Every entry's record_hash is SHA-256 over its own fields *plus* the
previous entry's record_hash. Editing or deleting any past row, or
inserting one out of sequence, changes what a fresh recomputation
produces for every row after it -- so verify_chain() can prove whether
the log has been altered since it was written, not just record that
something happened.

GENESIS_HASH is the sentinel "previous hash" for the first entry in a
tenant's chain (there is nothing before it to hash).
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.models import AuditLogEntry


GENESIS_HASH = "0" * 64


def _canonical_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _iso_utc(created_at: datetime) -> str:
    # SQLite (and some drivers) drop tzinfo on round-trip even for a
    # DateTime(timezone=True) column; every value we write is already UTC,
    # so a naive value here means "UTC with the label lost", not local
    # time. Treating it as local time would silently shift the hash input
    # and make verify_chain() fail on rows nobody tampered with.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at.astimezone(timezone.utc).isoformat()


def _compute_hash(
    *,
    tenant_id: int,
    sequence: int,
    event_type: str,
    request_id: int | None,
    created_at: datetime,
    canonical_payload: str,
    previous_hash: str,
) -> str:
    material = "|".join(
        [
            str(tenant_id),
            str(sequence),
            event_type,
            str(request_id) if request_id is not None else "",
            _iso_utc(created_at),
            canonical_payload,
            previous_hash,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_audit_entry(
    db,
    *,
    tenant_id: int,
    event_type: str,
    payload: dict,
    request_id: int | None = None,
) -> AuditLogEntry:
    """Append one entry to the tenant's chain and return it (not yet committed)."""
    latest = db.scalar(
        select(AuditLogEntry)
        .where(AuditLogEntry.tenant_id == tenant_id)
        .order_by(desc(AuditLogEntry.sequence))
    )
    sequence = (latest.sequence + 1) if latest is not None else 1
    previous_hash = latest.record_hash if latest is not None else GENESIS_HASH
    created_at = datetime.now(timezone.utc)
    canonical_payload = _canonical_payload(payload)
    record_hash = _compute_hash(
        tenant_id=tenant_id,
        sequence=sequence,
        event_type=event_type,
        request_id=request_id,
        created_at=created_at,
        canonical_payload=canonical_payload,
        previous_hash=previous_hash,
    )
    entry = AuditLogEntry(
        tenant_id=tenant_id,
        sequence=sequence,
        request_id=request_id,
        event_type=event_type,
        payload=payload,
        created_at=created_at,
        previous_hash=previous_hash,
        record_hash=record_hash,
    )
    db.add(entry)
    db.flush()
    return entry


@dataclass(frozen=True)
class ChainVerificationResult:
    valid: bool
    checked_count: int
    broken_at_sequence: int | None = None
    reason: str | None = None


def verify_chain(entries: list[AuditLogEntry]) -> ChainVerificationResult:
    """Recompute every hash in order and confirm the chain is unbroken.

    entries need not be pre-sorted; this sorts by sequence defensively so
    callers can pass a raw query result.
    """
    ordered = sorted(entries, key=lambda item: item.sequence)
    expected_previous = GENESIS_HASH
    for entry in ordered:
        if entry.previous_hash != expected_previous:
            return ChainVerificationResult(
                valid=False,
                checked_count=len(ordered),
                broken_at_sequence=entry.sequence,
                reason=(
                    f"sequence {entry.sequence}: previous_hash does not match "
                    "the prior entry's record_hash (missing, reordered, or "
                    "deleted entry)."
                ),
            )
        recomputed = _compute_hash(
            tenant_id=entry.tenant_id,
            sequence=entry.sequence,
            event_type=entry.event_type,
            request_id=entry.request_id,
            created_at=entry.created_at,
            canonical_payload=_canonical_payload(entry.payload),
            previous_hash=entry.previous_hash,
        )
        if recomputed != entry.record_hash:
            return ChainVerificationResult(
                valid=False,
                checked_count=len(ordered),
                broken_at_sequence=entry.sequence,
                reason=f"sequence {entry.sequence}: stored fields do not match record_hash (row was edited).",
            )
        expected_previous = entry.record_hash

    return ChainVerificationResult(valid=True, checked_count=len(ordered))
