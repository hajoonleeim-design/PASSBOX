import re
from dataclasses import dataclass

from app.security_scan import (
    ACCESS_TOKEN_PATTERN,
    API_KEY_PATTERN,
    BUSINESS_REG_NO_PATTERN,
    CREDIT_CARD_PATTERN,
    EMAIL_OBFUSCATED_PATTERN,
    EMAIL_PATTERN,
    KEYWORD_CATEGORY,
    PASSPORT_KR_PATTERN,
    PERSONAL_ID_PATTERN,
    PHONE_INTL_PATTERN,
    PHONE_PATTERN,
    PHONE_SPELLED_PATTERN,
    PRIVATE_KEY_PATTERN,
    SECRET_PATTERN,
)


MASKING_VERSION = "rules-mask-v2"


@dataclass(frozen=True)
class MaskingResult:
    masked_text: str
    categories: tuple[str, ...]
    replacement_count: int


# Patterns are shared with app.security_scan so a category detected by the
# scanner is guaranteed to also be masked here (kept as one source of truth).
# Order matters here (unlike the scanner, which never rewrites the text):
# SECRET runs before API_KEY/CREDIT_CARD so a "api_key: sk-..." style match
# is masked as one SECRET span instead of leaving a partial key behind.
_MASK_RULES: tuple[tuple[str, str], ...] = (
    (
        "PRIVATE_KEY",
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    ),
    ("SECRET", SECRET_PATTERN),
    ("API_KEY", API_KEY_PATTERN),
    ("ACCESS_TOKEN", ACCESS_TOKEN_PATTERN),
    ("CREDIT_CARD", CREDIT_CARD_PATTERN),
    ("PASSPORT_KR", PASSPORT_KR_PATTERN),
    ("BUSINESS_REG_NO", BUSINESS_REG_NO_PATTERN),
    ("PERSONAL_ID", PERSONAL_ID_PATTERN),
    ("PHONE", PHONE_PATTERN),
    ("PHONE", PHONE_INTL_PATTERN),
    ("PHONE", PHONE_SPELLED_PATTERN),
    ("EMAIL", EMAIL_PATTERN),
    ("EMAIL", EMAIL_OBFUSCATED_PATTERN),
)


def mask_text(text: str, keyword_patterns: tuple[str, ...] = ()) -> MaskingResult:
    masked = text
    categories: list[str] = []
    replacement_count = 0

    extra = tuple((KEYWORD_CATEGORY, pattern) for pattern in keyword_patterns)
    for category, pattern in extra + _MASK_RULES:
        replacement = f"[MASKED:{category}]"
        masked, count = re.subn(pattern, replacement, masked)
        if count:
            categories.append(category)
            replacement_count += count

    return MaskingResult(
        masked_text=masked,
        categories=tuple(categories),
        replacement_count=replacement_count,
    )
