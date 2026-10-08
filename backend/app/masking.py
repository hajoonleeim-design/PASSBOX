import re
from dataclasses import dataclass
from typing import Callable

from app.security_scan import (
    ACCESS_TOKEN_PATTERN,
    ACCOUNT_NO_PATTERN,
    API_KEY_PATTERN,
    BUSINESS_REG_NO_PATTERN,
    CREDIT_CARD_PATTERN,
    EMAIL_BRACKET_PATTERN,
    EMAIL_OBFUSCATED_PATTERN,
    EMAIL_PATTERN,
    KEYWORD_CATEGORY,
    PASSPORT_KR_PATTERN,
    PASSWORD_KO_PATTERN,
    PASSWORD_SPELLED_PATTERN,
    PERSONAL_ID_PATTERN,
    PERSONAL_ID_SPELLED_PATTERN,
    PHONE_INTL_PATTERN,
    PHONE_PATTERN,
    PHONE_SPELLED_PATTERN,
    PRIVATE_KEY_PATTERN,
    SECRET_PATTERN,
    _looks_like_account_number,
    _looks_like_password_value,
    _passes_luhn,
    _spells_out_personal_id,
    _spells_out_phone,
    normalize_for_scan,
)


MASKING_VERSION = "rules-mask-v3"


@dataclass(frozen=True)
class MaskingResult:
    masked_text: str
    categories: tuple[str, ...]
    replacement_count: int


# Patterns AND validators are shared with app.security_scan so a category detected by the
# scanner is guaranteed to be masked the same way here (one source of truth). Applying the
# validator matters: without it a pattern like the spelled-digit phone matches inside a longer
# run (e.g. a spelled resident ID) and leaves half of it unmasked, and any 16-digit number
# is masked as a card even when it fails the Luhn check.
# Order matters here (unlike the scanner, which never rewrites the text):
# SECRET runs before API_KEY/CREDIT_CARD so a "api_key: sk-..." style match
# is masked as one SECRET span instead of leaving a partial key behind, and the spelled
# resident ID runs before the spelled phone for the same reason.
_MASK_RULES: tuple[tuple[str, str, Callable[[str], bool] | None], ...] = (
    (
        "PRIVATE_KEY",
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        None,
    ),
    ("SECRET", SECRET_PATTERN, None),
    ("SECRET", PASSWORD_KO_PATTERN, _looks_like_password_value),
    ("SECRET", PASSWORD_SPELLED_PATTERN, None),
    ("API_KEY", API_KEY_PATTERN, None),
    ("ACCESS_TOKEN", ACCESS_TOKEN_PATTERN, None),
    ("CREDIT_CARD", CREDIT_CARD_PATTERN, _passes_luhn),
    ("PASSPORT_KR", PASSPORT_KR_PATTERN, None),
    ("BUSINESS_REG_NO", BUSINESS_REG_NO_PATTERN, None),
    ("ACCOUNT_NO", ACCOUNT_NO_PATTERN, _looks_like_account_number),
    ("PERSONAL_ID", PERSONAL_ID_PATTERN, None),
    ("PERSONAL_ID", PERSONAL_ID_SPELLED_PATTERN, _spells_out_personal_id),
    ("PHONE", PHONE_PATTERN, None),
    ("PHONE", PHONE_INTL_PATTERN, None),
    ("PHONE", PHONE_SPELLED_PATTERN, _spells_out_phone),
    ("EMAIL", EMAIL_PATTERN, None),
    ("EMAIL", EMAIL_OBFUSCATED_PATTERN, None),
    ("EMAIL", EMAIL_BRACKET_PATTERN, None),
)


def _substitute(pattern: str, validator: Callable[[str], bool] | None, replacement: str, text: str) -> tuple[str, int]:
    replaced = 0

    def swap(match: re.Match) -> str:
        nonlocal replaced
        if validator is not None and not validator(match.group(0)):
            return match.group(0)
        replaced += 1
        return replacement

    return re.sub(pattern, swap, text), replaced


def mask_text(text: str, keyword_patterns: tuple[str, ...] = ()) -> MaskingResult:
    masked = normalize_for_scan(text)
    categories: list[str] = []
    replacement_count = 0

    extra = tuple((KEYWORD_CATEGORY, pattern, None) for pattern in keyword_patterns)
    for category, pattern, validator in extra + _MASK_RULES:
        masked, count = _substitute(pattern, validator, f"[MASKED:{category}]", masked)
        if count:
            categories.append(category)
            replacement_count += count

    return MaskingResult(
        masked_text=masked,
        categories=tuple(categories),
        replacement_count=replacement_count,
    )
