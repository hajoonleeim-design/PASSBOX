import hashlib
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.auth import require_roles
from app.audit_chain import append_audit_entry
from app.db import get_session_factory
from app.models import SensitiveKeyword, User

router = APIRouter(prefix="/admin/sensitive-keywords", tags=["Admin Sensitive Keywords"])
_MANAGER_ROLES = ("SECURITY_ADMIN", "ADMIN")

# LOW is deliberately not offered: a low-severity hit neither raises the grade nor
# behaves differently from MEDIUM at the gateway, so it would only mislead admins.
Severity = Literal["HIGH", "MEDIUM"]


class KeywordCreatePayload(BaseModel):
    keyword: str = Field(min_length=2, max_length=100)
    label: str = Field(default="", max_length=100)
    severity: Severity = "MEDIUM"


class KeywordUpdatePayload(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    severity: Severity | None = None
    enabled: bool | None = None


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    label: str
    severity: str
    enabled: bool
    created_at: datetime


def _to_response(row: SensitiveKeyword) -> KeywordResponse:
    return KeywordResponse(id=row.id, keyword=row.keyword, label=row.label, severity=row.severity, enabled=row.enabled, created_at=row.created_at)


def _audit(db, user: User, event_type: str, row: SensitiveKeyword) -> None:
    # The keyword is itself confidential (e.g. a project codename), so the tamper-evident
    # log -- which is exported to SIEM -- records only its hash, never the plaintext.
    append_audit_entry(
        db,
        tenant_id=user.tenant_id,
        event_type=event_type,
        payload={
            "keyword_id": row.id,
            "keyword_sha256": hashlib.sha256(row.keyword.encode("utf-8")).hexdigest(),
            "label": row.label,
            "severity": row.severity,
            "enabled": row.enabled,
            "actor_user_id": user.id,
        },
    )


def _get_row(db, keyword_id: int, tenant_id: int) -> SensitiveKeyword:
    row = db.scalar(
        select(SensitiveKeyword).where(SensitiveKeyword.id == keyword_id, SensitiveKeyword.tenant_id == tenant_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="기밀 키워드를 찾을 수 없습니다.")
    return row


@router.get("", response_model=list[KeywordResponse], summary="기밀 키워드 목록")
def list_keywords(current_user: User = Depends(require_roles(*_MANAGER_ROLES))):
    with get_session_factory()() as db:
        rows = db.scalars(
            select(SensitiveKeyword)
            .where(SensitiveKeyword.tenant_id == current_user.tenant_id)
            .order_by(SensitiveKeyword.created_at.desc())
        ).all()
        return [_to_response(row) for row in rows]


@router.post("", response_model=KeywordResponse, status_code=201, summary="기밀 키워드 등록")
def create_keyword(payload: KeywordCreatePayload, current_user: User = Depends(require_roles(*_MANAGER_ROLES))):
    keyword = " ".join(payload.keyword.split())
    if len(keyword) < 2:
        raise HTTPException(status_code=422, detail="키워드는 공백을 제외하고 2자 이상이어야 합니다.")
    with get_session_factory()() as db:
        exists = db.scalar(
            select(SensitiveKeyword.id).where(
                SensitiveKeyword.tenant_id == current_user.tenant_id,
                SensitiveKeyword.keyword == keyword,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=409, detail="이미 등록된 키워드입니다.")
        row = SensitiveKeyword(
            tenant_id=current_user.tenant_id,
            keyword=keyword,
            label=payload.label.strip(),
            severity=payload.severity,
            enabled=True,
            created_by=current_user.id,
        )
        db.add(row)
        db.flush()
        _audit(db, current_user, "SENSITIVE_KEYWORD_CREATED", row)
        db.commit()
        db.refresh(row)
        return _to_response(row)


@router.patch("/{keyword_id}", response_model=KeywordResponse, summary="기밀 키워드 수정")
def update_keyword(keyword_id: int, payload: KeywordUpdatePayload, current_user: User = Depends(require_roles(*_MANAGER_ROLES))):
    with get_session_factory()() as db:
        row = _get_row(db, keyword_id, current_user.tenant_id)
        if payload.label is not None:
            row.label = payload.label.strip()
        if payload.severity is not None:
            row.severity = payload.severity
        if payload.enabled is not None:
            row.enabled = payload.enabled
        db.flush()
        _audit(db, current_user, "SENSITIVE_KEYWORD_UPDATED", row)
        db.commit()
        db.refresh(row)
        return _to_response(row)


@router.delete("/{keyword_id}", status_code=204, summary="기밀 키워드 삭제")
def delete_keyword(keyword_id: int, current_user: User = Depends(require_roles(*_MANAGER_ROLES))):
    with get_session_factory()() as db:
        row = _get_row(db, keyword_id, current_user.tenant_id)
        _audit(db, current_user, "SENSITIVE_KEYWORD_DELETED", row)
        db.delete(row)
        db.commit()
    return Response(status_code=204)
