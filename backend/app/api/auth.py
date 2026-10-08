from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import Settings, get_session_factory
from app.rate_limit import login_rate_limiter
from app.models import AuditLogEntry, RevokedToken, Tenant, TokenCutoff, User
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.audit_chain import append_audit_entry


router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(
    description="POST /auth/login 응답의 access_token 값을 그대로 붙여넣으세요 (Bearer 접두어는 자동으로 붙습니다).",
)


class LoginRequest(BaseModel):
    tenant_id: int = Field(gt=0)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class PasswordChangeResponse(BaseModel):
    status: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    tenant_id: int
    username: str
    display_name: str
    role: str
    tenant_name: str


class MeResponse(BaseModel):
    user_id: int
    tenant_id: int
    username: str
    display_name: str
    role: str
    tenant_name: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request):
    settings = Settings()
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_host}:{payload.tenant_id}:{payload.username.casefold()}"
    retry_after = login_rate_limiter.retry_after_seconds(
        rate_limit_key,
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(retry_after)},
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        if _recent_account_failures(db, payload.tenant_id, payload.username) >= ACCOUNT_LOCK_FAILURES:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="이 계정에 로그인 실패가 반복되어 잠시 잠겼습니다. 15분 후 다시 시도하거나 관리자에게 문의해 주세요.",
                headers={"Retry-After": str(int(ACCOUNT_LOCK_WINDOW.total_seconds()))},
            )
        user = db.scalar(
            select(User).where(
                User.tenant_id == payload.tenant_id,
                User.username == payload.username,
                User.status == "ACTIVE",
            )
        )

        if user is None or not verify_password(payload.password, user.password_hash):
            if db.get(Tenant, payload.tenant_id) is not None:
                append_audit_entry(
                    db,
                    tenant_id=payload.tenant_id,
                    event_type="LOGIN_FAILED",
                    payload={"username": payload.username[:100], "client_ip": client_host},
                )
                db.commit()
            login_rate_limiter.record_failure(
                rate_limit_key,
                max_attempts=settings.login_rate_limit_attempts,
                window_seconds=settings.login_rate_limit_window_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디, 기관 또는 비밀번호가 올바르지 않습니다.",
            )

        login_rate_limiter.reset(rate_limit_key)
        append_audit_entry(
            db,
            tenant_id=user.tenant_id,
            event_type="LOGIN_SUCCEEDED",
            payload={"user_id": user.id, "role": user.role, "client_ip": client_host},
        )
        db.commit()
        token = create_access_token(user.id, user.tenant_id, user.role)
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            tenant_name=user.tenant.name,
        )


# Per-account limit on top of the in-memory per-IP limiter: counted from the audit chain
# in the database, so it survives restarts, is shared across workers, and still applies
# when an attacker rotates IP addresses.
ACCOUNT_LOCK_FAILURES = 10
ACCOUNT_LOCK_WINDOW = timedelta(minutes=15)


def _recent_account_failures(db, tenant_id: int, username: str) -> int:
    since = datetime.now(timezone.utc) - ACCOUNT_LOCK_WINDOW
    recent = db.scalars(
        select(AuditLogEntry.payload).where(
            AuditLogEntry.tenant_id == tenant_id,
            AuditLogEntry.event_type == "LOGIN_FAILED",
            AuditLogEntry.created_at >= since,
        )
    ).all()
    wanted = username[:100]
    return sum(1 for item in recent if isinstance(item, dict) and item.get("username") == wanted)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        tenant_id = int(payload["tenant_id"])
        jti = payload.get("jti")
        issued_at = payload.get("iat")
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        user = db.scalar(
            select(User).options(joinedload(User.tenant)).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.status == "ACTIVE",
            )
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 확인할 수 없습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if _token_is_revoked(db, user.id, jti, issued_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그아웃되었거나 비밀번호 변경으로 만료된 세션입니다. 다시 로그인해 주세요.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user


def _token_is_revoked(db, user_id: int, jti: str | None, issued_at) -> bool:
    if jti and db.get(RevokedToken, jti) is not None:
        return True
    cutoff = db.get(TokenCutoff, user_id)
    if cutoff is None:
        return False
    not_before = cutoff.not_before if cutoff.not_before.tzinfo else cutoff.not_before.replace(tzinfo=timezone.utc)
    # Tokens without iat predate revocation support; treat them as issued before any cutoff.
    return issued_at is None or datetime.fromtimestamp(int(issued_at), timezone.utc) < not_before


@router.post("/logout", status_code=204, summary="현재 토큰을 서버에서 무효화")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    payload = decode_access_token(credentials.credentials)
    jti, exp = payload.get("jti"), payload.get("exp")
    if jti:
        now = datetime.now(timezone.utc)
        session_factory = get_session_factory()
        with session_factory() as db:
            db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()
            if db.get(RevokedToken, jti) is None:
                expires_at = datetime.fromtimestamp(int(exp), timezone.utc) if exp else now
                db.add(RevokedToken(jti=jti, user_id=current_user.id, expires_at=expires_at))
            db.commit()
    return Response(status_code=204)


@router.post("/password", response_model=PasswordChangeResponse)
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
        )

    session_factory = get_session_factory()
    with session_factory() as db:
        user = db.scalar(
            select(User).where(
                User.id == current_user.id,
                User.tenant_id == current_user.tenant_id,
                User.status == "ACTIVE",
            )
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자 계정을 확인할 수 없습니다.",
            )
        user.password_hash = hash_password(payload.new_password)
        # Every token issued before this moment (including a stolen one) stops working.
        # Whole seconds, because JWT iat is stored in whole seconds.
        not_before = datetime.now(timezone.utc).replace(microsecond=0)
        cutoff = db.get(TokenCutoff, user.id)
        if cutoff is None:
            db.add(TokenCutoff(user_id=user.id, not_before=not_before))
        else:
            cutoff.not_before = not_before
        append_audit_entry(
            db,
            tenant_id=user.tenant_id,
            event_type="PASSWORD_CHANGED",
            payload={"user_id": user.id},
        )
        db.commit()

    return PasswordChangeResponse(status="updated")


def require_roles(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 기능을 사용할 권한이 없습니다.",
            )
        return current_user

    return dependency


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
        tenant_name=current_user.tenant.name,
    )
