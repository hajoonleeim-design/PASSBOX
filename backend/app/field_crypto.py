"""Encryption at rest for the columns that hold readable document or chat text.

The gateway handles S-grade (and sometimes C-grade) material. Hash chains prove the
audit log was not altered, but they do nothing if someone simply reads the database, so
the readable text itself is stored encrypted:

    DocumentText.extracted_text, OutboundApproval.masked_payload,
    ChatRequest.prompt_text, ChatRequest.response_text

AES-256-GCM (authenticated: a modified ciphertext fails to decrypt instead of returning
garbage). Each value gets a fresh 96-bit nonce. Stored form: ``enc:v1:<base64(nonce|ct)>``.

Rows written before this existed are plaintext; they are still readable (no prefix ->
returned as-is) and are re-encrypted the next time they are saved, or all at once by
``migrate_encrypt_text.py``.

Key: DATA_ENCRYPTION_KEY (any long secret string, hashed to 32 bytes). Required in
production. In development/test it falls back to a key derived from JWT_SECRET_KEY so a
fresh checkout still runs; that fallback is never accepted in production.
"""
import base64
import hashlib
import logging
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

PREFIX = "enc:v1:"
_log = logging.getLogger("passbox.field_crypto")


@lru_cache(maxsize=8)
def _key_for(data_key: str, jwt_secret: str) -> bytes:
    if data_key:
        return hashlib.sha256(data_key.encode("utf-8")).digest()
    _log.warning("DATA_ENCRYPTION_KEY is not set; using a development key derived from JWT_SECRET_KEY")
    return HKDF(algorithm=SHA256(), length=32, salt=b"passbox-field-encryption", info=b"dev-fallback").derive(
        (jwt_secret or "passbox-development-only").encode("utf-8")
    )


def _key() -> bytes:
    from app.db import Settings

    settings = Settings()
    return _key_for(settings.data_encryption_key.strip(), settings.jwt_secret_key)


def encrypt_text(value: str) -> str:
    nonce = os.urandom(12)
    sealed = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), PREFIX.encode("ascii"))
    return PREFIX + base64.b64encode(nonce + sealed).decode("ascii")


def decrypt_text(value: str) -> str:
    raw = base64.b64decode(value[len(PREFIX):])
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], PREFIX.encode("ascii")).decode("utf-8")


def is_encrypted(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


class EncryptedText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or is_encrypted(value):
            return value
        return encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None or not is_encrypted(value):
            return value  # legacy plaintext row
        return decrypt_text(value)
