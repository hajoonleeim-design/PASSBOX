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
# PROMPT_INJECTION은 "지시를 그대로 따르는 명령형 문장"만 잡도록 설계했습니다.
# 'jailbreak'나 'DAN' 같은 단어가 보안 교육 질문("탈옥이 뭐야?")에도 등장할 수
# 있어서, 페르소나/탈옥 관련 표현은 반드시 명령형(~해줘, act as, enable 등)과
# 함께 나타날 때만 매칭하여 오탐(false positive)을 줄입니다.
PROMPT_INJECTION_PATTERN = (
    r"(?i)("
    # 1. 지시 무효화 시도
    r"ignore\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above)\s+instructions?"
    r"|disregard\s+(?:the\s+)?(?:above|previous|prior)\s+instructions?"
    r"|forget\s+(?:everything|all)\s+(?:you\s+were\s+told|above)"
    r"|이전\s*(?:지시|명령)\s*사항?\s*(?:은|는|을|를)?\s*(?:모두\s*)?무시"
    r"|위\s*(?:내용|지시|명령)\s*(?:은|는|을|를)?\s*무시하고"
    r"|지금까지\s*(?:의\s*)?규칙\s*(?:은|는|을|를)?\s*(?:잊어|무시)"
    # 2. 시스템 프롬프트 탈취 시도
    r"|(?:reveal|print|show|output|repeat)\s+.{0,30}(?:system\s+prompt|your\s+instructions)"
    r"|repeat\s+everything\s+above"
    r"|시스템\s*프롬프트\s*(?:를|을)?\s*(?:그대로\s*)?(?:보여|출력|알려)"
    r"|(?:너의|당신의)\s*(?:지시사항|시스템\s*프롬프트)\s*(?:을|를)?\s*(?:알려|보여|출력)"
    r"|위에\s*(?:적힌|있는)\s*(?:내용|지시)\s*(?:을|를)?\s*그대로\s*(?:보여|반복|출력)"
    # 3. 탈옥/페르소나 우회 (반드시 명령형과 결합될 때만 매칭)
    r"|(?:너는|당신은|you\s+are)\s*(?:이제|now)?\s*(?:DAN|무제한\s*AI|제약\s*없는\s*AI)"
    r"|act\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken)\s+AI"
    r"|pretend\s+(?:you\s+are|to\s+be)\s+.{0,20}(?:unrestricted|no\s+rules|DAN)"
    r"|(?:enable|activate)\s*.{0,10}(?:developer\s+mode)"
    r"|(?:개발자\s*모드|탈옥\s*모드|무제한\s*모드)\s*(?:을|를)?\s*(?:켜|시작해|활성화)"
    r"|제약\s*(?:이|가)?\s*없는\s*(?:AI|인공지능)(?:처럼|인\s*것처럼)?\s*(?:행동|답변)해"
    # 4. 권한/핑계를 이용한 안전장치 해제 시도
    r"|as\s+the\s+system\s+administrator,?\s*override"
    r"|관리자\s*권한으로\s*(?:안전\s*장치|필터)\s*(?:를)?\s*(?:해제|꺼)"
    r"|(?:테스트|가상)\s*(?:목적|시나리오)(?:이니|니까)\s*.{0,15}(?:무시해도|해제해|꺼줘)"
    # 5. 가짜 역할/구분자 주입 (일반 대화에 등장할 가능성이 거의 없는 패턴)
    r"|<\|im_start\|>"
    r"|\[INST\]"
    r"|###\s*(?:system|instruction)"
    r"|비밀\s*.{0,20}지시"
    r")"
)
# 악성 링크 탐지: 일반 URL 전체가 아니라, 피싱/멀웨어 배포에 흔히 쓰이는
# "정상 링크에서는 드문 특징"만 좁게 잡습니다 (IP 주소 직접 노출, 잘 알려진
# 단축 URL, 퓨니코드/동형이의 도메인, 실행파일 직접 다운로드 링크).
# 사용자가 보내는 프롬프트가 아니라 AI 응답을 검사할 때만 쓰도록 설계되었습니다
# (scan_response_links 참고) -- "이 링크 안전해?" 같은 정상 질문까지
# 차단하지 않기 위해서입니다.
SUSPICIOUS_URL_PATTERN = (
    r"(?i)https?://(?:"
    r"\d{1,3}(?:\.\d{1,3}){3}(?::\d{2,5})?(?:/\S*)?"
    r"|(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd|ow\.ly|rebrand\.ly|cutt\.ly|buff\.ly)/\S+"
    r"|xn--[a-z0-9-]+(?:\.[a-z0-9-]+)+\S*"
    r"|\S+\.(?:exe|scr|bat|cmd|msi|apk|jar)(?:\?\S*)?(?=\s|$)"
    r")"
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

_LINK_RULES: tuple[_Rule, ...] = (
    _Rule("SUSPICIOUS_URL", "MEDIUM", SUSPICIOUS_URL_PATTERN),
)


def _hash_evidence(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan_text(text: str, rules: tuple[_Rule, ...] = _RULES) -> list[Finding]:
    """Scan extracted text and return safe metadata without retaining matches."""
    findings: list[Finding] = []
    for rule in rules:
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


def scan_response_links(text: str) -> list[Finding]:
    """Malicious-link check for AI RESPONSES only.

    Deliberately not part of the default scan_text() rule set: those
    also run on user prompts (chat.py, gateway.py), and a user asking
    "is this link safe?" shouldn't get blocked for pasting a suspicious
    URL. This only ever runs on what the AI sends back (post_inspector.py).
    """
    return scan_text(text, rules=_LINK_RULES)
