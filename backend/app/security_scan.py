import hashlib
import re
from dataclasses import dataclass


SCANNER_VERSION = "rules-v1"


@dataclass(frozen=True)
class Finding:
    category: str
    severity: str
    match_count: int
    evidence_hash: str
    line_hint: int | None


_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "PERSONAL_ID",
        "HIGH",
        r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)",
    ),
    (
        "PHONE",
        "MEDIUM",
        r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)",
    ),
    (
        "EMAIL",
        "MEDIUM",
        r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    ),
    (
        "PRIVATE_KEY",
        "HIGH",
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
    ),
    (
        "API_KEY",
        "HIGH",
        r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})(?![A-Za-z0-9])",
    ),
    (
        "ACCESS_TOKEN",
        "HIGH",
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])",
    ),
    (
        "SECRET",
        "HIGH",
        r"(?i)\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret|secret|password)\s*[:=]\s*[^\s,;]{8,}",
    ),
    (
        "PROMPT_INJECTION",
        "HIGH",
        r"(?i)(?:ignore\s+(?:all\s+)?previous\s+instructions|system\s+prompt|reveal\s+.{0,30}prompt|jailbreak|이전\s*지시(?:사항)?\s*무시|시스템\s*프롬프트|프롬프트를\s*무시|비밀\s*.{0,20}지시)",
    ),
)


def _hash_evidence(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan_text(text: str) -> list[Finding]:
    """Scan extracted text and return safe metadata without retaining matches."""
    findings: list[Finding] = []
    for category, severity, pattern in _RULES:
        matches = list(re.finditer(pattern, text))
        if not matches:
            continue

        first = matches[0]
        findings.append(
            Finding(
                category=category,
                severity=severity,
                match_count=len(matches),
                evidence_hash=_hash_evidence(first.group(0)),
                line_hint=text.count("\n", 0, first.start()) + 1,
            )
        )
    return findings
