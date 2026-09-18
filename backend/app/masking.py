import re
from dataclasses import dataclass


MASKING_VERSION = "rules-mask-v1"


@dataclass(frozen=True)
class MaskingResult:
    masked_text: str
    categories: tuple[str, ...]
    replacement_count: int


# 순서는 SECRET 표현식을 먼저 처리해 API 키 값이 다시 부분 매칭되지 않도록 합니다.
_MASK_RULES: tuple[tuple[str, str], ...] = (
    (
        "PRIVATE_KEY",
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    ),
    (
        "SECRET",
        r"(?i)\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret|secret|password)\s*[:=]\s*[^\s,;]{8,}",
    ),
    (
        "API_KEY",
        r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})(?![A-Za-z0-9])",
    ),
    (
        "ACCESS_TOKEN",
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])",
    ),
    ("PERSONAL_ID", r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)"),
    ("PHONE", r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)"),
    (
        "EMAIL",
        r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    ),
)


def mask_text(text: str) -> MaskingResult:
    masked = text
    categories: list[str] = []
    replacement_count = 0

    for category, pattern in _MASK_RULES:
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
