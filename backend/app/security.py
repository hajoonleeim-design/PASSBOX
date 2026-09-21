from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.db import Settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int, tenant_id: int, role: str) -> str:
    settings = Settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    if settings.jwt_access_token_minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be positive")

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_minutes
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = Settings()
    if not settings.jwt_secret_key:
        raise ValueError("JWT_SECRET_KEY is not configured")

    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise ValueError("invalid access token") from exc
