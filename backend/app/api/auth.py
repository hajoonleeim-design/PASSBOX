from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import get_session_factory
from app.models import User
from app.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


class LoginRequest(BaseModel):
    tenant_id: int = Field(gt=0)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


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
def login(payload: LoginRequest):
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디, 기관 또는 비밀번호가 올바르지 않습니다.",
            )

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
