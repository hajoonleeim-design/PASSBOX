import hashlib
import re
import unicodedata
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


# EICAR 표준 안티바이러스 테스트 시그니처. 실제 악성코드가 아니라 전 세계
# 백신 업체들이 "탐지 기능이 켜져 있는지" 자체 검증할 때 쓰는 업계 표준
# 68바이트 문자열입니다 (https://www.eicar.org/download-anti-malware-testfile/).
#
# 이 시그니처만 탐지하는 것은 실제 랜섬웨어/바이러스에 대한 방어가 아닙니다.
# "파일 업로드 -> 악성코드 검사 -> 격리/거부" 체크포인트가 실제로 배선되어
# 동작한다는 것을 증명하는 자리 표시자이며, 운영 배포 시에는 이 위치에
# ClamAV 같은 실제 백신 엔진을 붙여야 합니다.
EICAR_TEST_SIGNATURE = (
    rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


def contains_eicar_signature(data: bytes) -> bool:
    return EICAR_TEST_SIGNATURE in data


# Pattern strings are exported so app.masking can reuse the exact same
# definitions instead of maintaining a second, drift-prone copy.
PERSONAL_ID_PATTERN = r"(?<!\d)\d{6}\s{0,2}-?\s{0,2}[1-4]\d{6}(?!\d)"
# Separators: "-", ".", spaces or a line break (010.1234.5678, numbers split over lines).
PHONE_PATTERN = r"(?<!\d)01[016789][-.\s]{0,2}\d{3,4}[-.\s]{0,2}\d{4}(?!\d)"
# +82/0082로 국가번호를 쓰면 앞자리 0이 빠져 "10/11/16/17/18/19"로 시작한다
# (예: +82 10 1234 5678). 국내 표기(PHONE_PATTERN)만으로는 못 잡는, 실제
# QA에서 보고된 회피 패턴이다.
PHONE_INTL_PATTERN = r"(?<![\d+])(?:\+82|0082)[\s-]?1[016789][\s-]?\d{3,4}[\s-]?\d{4}(?!\d)"
# "공일공 일이삼사 오육칠팔"처럼 숫자를 한글로 풀어 쓰는 회피 패턴. 숫자
# 단어가 10~11개 연달아 나오는 경우만 후보로 잡고(아래 _spells_out_phone이
# 실제 유효한 휴대폰 번호 자릿수인지 검증), 일상 문장에서 우연히 숫자 단어가
# 이어질 일은 거의 없어 오탐 위험이 낮다.
_KOREAN_DIGIT_WORD = r"(?:공|일|이|삼|사|오|육|륙|칠|팔|구)"
PHONE_SPELLED_PATTERN = rf"{_KOREAN_DIGIT_WORD}(?:\s*{_KOREAN_DIGIT_WORD}){{9,10}}"
EMAIL_PATTERN = r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])"
# "user 앳 gmail 닷 com"처럼 @과 .을 한글 단어로 치환하는 회피 패턴. 실제
# 도메인 접미사(com/net/go.kr 등)로 끝날 때만 매칭해 "닷새" 같은 일반 단어와
# 오인하지 않도록 범위를 좁혔다.
# Written to be linear-time: the old form backtracked quadratically (20k chars of "a"
# took ~6s, enough for a single chat message to stall the server). Matching may only
# start at a token boundary, the pieces are ASCII-only (so "앳"/"닷" can't be swallowed
# into a name), and possessive quantifiers never give characters back.
EMAIL_OBFUSCATED_PATTERN = (
    r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]++\s*+(?:앳|\bat\b)\s*+"
    r"(?:[A-Za-z0-9-]++\s*+(?:닷|\bdot\b)\s*+)++"
    r"(?:com|co\.kr|net|org|kr|go\.kr)\b"
)
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
    r"|(?:ignore|disregard|forget)\s+(?:all\s+|everything\s+|anything\s+)?(?:you\s+were\s+(?:told|given)\s+)?(?:above|before|so\s+far|previously)\b"
    r"|forget\s+(?:everything|all)\s+(?:you\s+were\s+told|above)"
    r"|이전\s*(?:지시|명령)\s*사항?\s*(?:은|는|을|를)?\s*(?:모두\s*)?무시"
    r"|위\s*(?:내용|지시|명령)\s*(?:은|는|을|를)?\s*무시하고"
    r"|지금까지\s*(?:의\s*)?규칙\s*(?:은|는|을|를)?\s*(?:잊어|무시)"
    # 2. 시스템 프롬프트 탈취 시도
    r"|(?:reveal|print|show|output|repeat)\s+.{0,30}(?:system\s+prompt|your\s+instructions)"
    r"|(?:reveal|print|show|output|repeat)\s+.{0,30}(?:hidden|secret|internal|initial|original)\s+(?:instructions|prompt|rules)"
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


_KOREAN_DIGIT_VALUES = {
    "공": "0", "일": "1", "이": "2", "삼": "3", "사": "4",
    "오": "5", "육": "6", "륙": "6", "칠": "7", "팔": "8", "구": "9",
}


def _spells_out_phone(raw_match: str) -> bool:
    digits = "".join(_KOREAN_DIGIT_VALUES[ch] for ch in raw_match if ch in _KOREAN_DIGIT_VALUES)
    return bool(re.fullmatch(r"01[016789]\d{7,8}", digits))


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
    _Rule("PHONE", "MEDIUM", PHONE_INTL_PATTERN),
    _Rule("PHONE", "MEDIUM", PHONE_SPELLED_PATTERN, validator=_spells_out_phone),
    _Rule("EMAIL", "MEDIUM", EMAIL_PATTERN),
    _Rule("EMAIL", "MEDIUM", EMAIL_OBFUSCATED_PATTERN),
    _Rule("PRIVATE_KEY", "HIGH", PRIVATE_KEY_PATTERN),
    _Rule("API_KEY", "HIGH", API_KEY_PATTERN),
    _Rule("ACCESS_TOKEN", "HIGH", ACCESS_TOKEN_PATTERN),
    _Rule("SECRET", "HIGH", SECRET_PATTERN),
    _Rule("CREDIT_CARD", "HIGH", CREDIT_CARD_PATTERN, validator=_passes_luhn),
    _Rule("PASSPORT_KR", "HIGH", PASSPORT_KR_PATTERN),
    _Rule("BUSINESS_REG_NO", "MEDIUM", BUSINESS_REG_NO_PATTERN),
    _Rule("PROMPT_INJECTION", "HIGH", PROMPT_INJECTION_PATTERN),
)

# Download-and-execute one-liners ("curl ... | bash", "iwr ... | iex"): a model asked
# to "help install X" can be steered into handing the user one, and users paste them.
# Piping a download straight into a shell is the dangerous part; plain `curl <url>` is not.
RISKY_COMMAND_PATTERN = (
    r"(?i)\b(?:curl|wget)\b[^\n|;]{0,300}\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b"
    r"|\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n|;]{0,300}\|\s*(?:iex|invoke-expression)\b"
)

_LINK_RULES: tuple[_Rule, ...] = (
    _Rule("SUSPICIOUS_URL", "MEDIUM", SUSPICIOUS_URL_PATTERN),
    _Rule("RISKY_COMMAND", "HIGH", RISKY_COMMAND_PATTERN),
)


def _hash_evidence(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


KEYWORD_CATEGORY = "CONFIDENTIAL_KEYWORD"


def keyword_pattern(keyword: str) -> str:
    """Literal, case-insensitive match that tolerates whitespace between ANY two characters,
    so "블 루 문" or "blue moon" can't be used to slip past a registered "블루문"/"BlueMoon"."""
    chars = [re.escape(ch) for ch in keyword if not ch.isspace()]
    return "(?i)" + r"\s*".join(chars)


def keyword_rules(keywords: list[tuple[str, str]]) -> tuple[_Rule, ...]:
    """Build scan rules from (keyword, severity) pairs registered by a tenant admin."""
    return tuple(
        _Rule(KEYWORD_CATEGORY, severity, keyword_pattern(keyword))
        for keyword, severity in keywords
        if keyword.strip()
    )


_INVISIBLE_CHARS = dict.fromkeys(map(ord, "​‌‍⁠﻿­"))


def normalize_for_scan(text: str) -> str:
    """Undo cheap evasion before matching: fullwidth/compatibility forms become plain
    characters (０１０ -> 010) and invisible zero-width characters are removed
    (kim​@agency.go.kr). Masking applies the same normalization, so what we detect
    is exactly what we replace."""
    return unicodedata.normalize("NFKC", text).translate(_INVISIBLE_CHARS)


def scan_text(
    text: str,
    rules: tuple[_Rule, ...] = _RULES,
    extra_rules: tuple[_Rule, ...] = (),
) -> list[Finding]:
    """Scan extracted text and return safe metadata without retaining matches."""
    text = normalize_for_scan(text)
    findings: list[Finding] = []
    for rule in rules + extra_rules:
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
