import hashlib
import re
from dataclasses import dataclass
from typing import Callable


SCANNER_VERSION = "rules-v2"


@dataclass(frozen=True)
class Finding:
    category: str
    severity: str
    match_count: int
    evidence_hash: str
    line_hint: int | None


# Pattern strings are exported so app.masking can reuse the exact same
# definitions instead of maintaining a second, drift-prone copy.
PERSONAL_ID_PATTERN = r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)"
PHONE_PATTERN = r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)"
EMAIL_PATTERN = r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])"
PRIVATE_KEY_PATTERN = r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
API_KEY_PATTERN = (
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{35}|xox[baprs]-[0-9A-Za-z-]{10,})(?![A-Za-z0-9])"
)
ACCESS_TOKEN_PATTERN = (
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\."
    r"[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])"
)
SECRET_PATTERN = (
    r"(?i)\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret|secret|password)"
    r"\s*[:=]\s*[^\s,;]{8,}"
)
# Visa/Mastercard/Amex/Discover prefixes, grouped digits with optional
# separators. Luhn validation (see _passes_luhn) rejects arbitrary
# lookalike digit runs that happen to start with a card prefix.
CREDIT_CARD_PATTERN = (
    r"(?<!\d)(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))"
    r"[- ]?\d{4}[- ]?\d{4}[- ]?\d{0,4}(?!\d)"
)
# Korean passport number: one type letter (일반/관용/외교/선원 등) + 8 digits.
PASSPORT_KR_PATTERN = r"(?<![A-Za-z0-9])[MSRODT]\d{8}(?![A-Za-z0-9])"
# Korean business registration number: 3-2-5 digit groups.
BUSINESS_REG_NO_PATTERN = r"(?<!\d)\d{3}-\d{2}-\d{5}(?!\d)"
PROMPT_INJECTION_PATTERN = (
    r"(?i)(?:ignore\s+(?:all\s+)?previous\s+instructions|system\s+prompt|"
    r"reveal\s+.{0,30}prompt|jailbreak|이전\s*지시(?:사항)?\s*무시|"
    r"시스템\s*프롬프트|프롬프트를\s*무시|비밀\s*.{0,20}지시)"
)


def _passes_luhn(raw_match: str) -> bool:
    digits = [ch for ch in raw_match if ch.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = int(digit)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


@dataclass(frozen=True)
class _Rule:
    category: str
    severity: str
    pattern: str
    validator: Callable[[str], bool] | None = None


_RULES: tuple[_Rule, ...] = (
    _Rule("PERSONAL_ID", "HIGH", PERSONAL_ID_PATTERN),
    _Rule("PHONE", "MEDIUM", PHONE_PATTERN),
    _Rule("EMAIL", "MEDIUM", EMAIL_PATTERN),
    _Rule("PRIVATE_KEY", "HIGH", PRIVATE_KEY_PATTERN),
    _Rule("API_KEY", "HIGH", API_KEY_PATTERN),
    _Rule("ACCESS_TOKEN", "HIGH", ACCESS_TOKEN_PATTERN),
    _Rule("SECRET", "HIGH", SECRET_PATTERN),
    _Rule("CREDIT_CARD", "HIGH", CREDIT_CARD_PATTERN, validator=_passes_luhn),
    _Rule("PASSPORT_KR", "HIGH", PASSPORT_KR_PATTERN),
    _Rule("BUSINESS_REG_NO", "MEDIUM", BUSINESS_REG_NO_PATTERN),
    _Rule("PROMPT_INJECTION", "HIGH", PROMPT_INJECTION_PATTERN),
)


def _hash_evidence(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan_text(text: str) -> list[Finding]:
    """Scan extracted text and return safe metadata without retaining matches."""
    findings: list[Finding] = []
    for rule in _RULES:
        matches = list(re.finditer(rule.pattern, text))
        if rule.validator is not None:
            matches = [m for m in matches if rule.validator(m.group(0))]
        if not matches:
            continue

        first = matches[0]
        findings.append(
            Finding(
                category=rule.category,
                severity=rule.severity,
                match_count=len(matches),
                evidence_hash=_hash_evidence(first.group(0)),
                line_hint=text.count("\n", 0, first.start()) + 1,
            )
        )
    return findings
