from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import Settings, get_session_factory
from app.rate_limit import login_rate_limiter
from app.models import User
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


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
        user = db.scalar(
            select(User).where(
                User.tenant_id == payload.tenant_id,
                User.username == payload.username,
                User.status == "ACTIVE",
            )
        )

        if user is None or not verify_password(payload.password, user.password_hash):
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        tenant_id = int(payload["tenant_id"])
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

        return user


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
