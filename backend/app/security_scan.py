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
# A digit written either as a Korean word or as a real digit, so mixed forms such as
# "010 일이삼사 5678" and "공일공-일이삼사-오육칠팔" are covered. Matching must begin at the
# start of a run (lookbehind) so a long run can't be sliced from the middle, and the
# validator below insists on at least one spelled-out word (plain digits are PHONE_PATTERN's job).
_SPELLED_DIGIT = rf"(?:{_KOREAN_DIGIT_WORD}|\d)"
_SPELLED_SEP = r"[\s.-]{0,2}"
PHONE_SPELLED_PATTERN = rf"(?<![가-힣\d]){_SPELLED_DIGIT}(?:{_SPELLED_SEP}{_SPELLED_DIGIT}){{9,12}}"
# 주민등록번호도 같은 방식으로 풀어 쓸 수 있다("구공공일공일 일이삼사오육칠").
PERSONAL_ID_SPELLED_PATTERN = rf"(?<![가-힣\d]){_SPELLED_DIGIT}(?:{_SPELLED_SEP}{_SPELLED_DIGIT}){{12}}(?!\d)"
# 한국어 비밀번호 표현. 기존 SECRET_PATTERN은 영문 "password=" 형태만 봤기 때문에
# "비번: qwer1234", "비밀번호는 Admin!2026", "pw=Secret!9876"이 그대로 통과했다.
_PASSWORD_LABEL = r"(?:비밀\s?번호|비번|패스워드|암호|(?<![A-Za-z0-9])(?:passwd|pw))"
PASSWORD_KO_PATTERN = rf"(?i){_PASSWORD_LABEL}\s*(?:은|는|이|가)?\s*[:=]?\s*[!-~]{{4,}}"
# "비번은 일삼오칠" — PIN을 한글 숫자로 풀어 쓴 경우(4자리 이상 연속).
PASSWORD_SPELLED_PATTERN = rf"{_PASSWORD_LABEL}\s*(?:은|는|이|가)?\s*[:=]?\s*{_KOREAN_DIGIT_WORD}(?:\s*{_KOREAN_DIGIT_WORD}){{3,9}}"
# 은행명 또는 '계좌(번호)'와 함께 나오는 10~14자리 번호. 은행명 없이 숫자만 있으면 잡지
# 않는다(전화번호·날짜·주문번호와 구분할 방법이 없기 때문).
_BANK_NAME = (
    r"(?:KB국민|국민|신한|우리|하나|농협|NH|IBK|기업|SC제일|제일|씨티|카카오뱅크|카카오|케이뱅크|"
    r"토스뱅크|토스|수협|새마을금고|우체국|신협|산업|부산|대구|광주|전북|경남|제주)"
)
ACCOUNT_NO_PATTERN = (
    rf"(?:{_BANK_NAME}(?:은행)?|계좌(?:\s?번호)?)\s*(?:은|는|:)?\s*"
    r"\d{2,6}(?:[- ]\d{2,8}){1,3}(?!\d)"
)
EMAIL_PATTERN = r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])"
# "user 앳 gmail 닷 com"처럼 @과 .을 한글 단어로 치환하는 회피 패턴. 실제
# 도메인 접미사(com/net/go.kr 등)로 끝날 때만 매칭해 "닷새" 같은 일반 단어와
# 오인하지 않도록 범위를 좁혔다.
# Written to be linear-time: the old form backtracked quadratically (20k chars of "a"
# took ~6s, enough for a single chat message to stall the server). Matching may only
# start at a token boundary, the pieces are ASCII-only (so "앳"/"닷" can't be swallowed
# into a name), and possessive quantifiers never give characters back.
EMAIL_OBFUSCATED_PATTERN = (
    r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]++\s*+(?:앳|골뱅이|\bat\b)\s*+"
    r"(?:[A-Za-z0-9-]++\s*+(?:닷|\bdot\b)\s*+)++"
    r"(?:com|co\.kr|net|org|kr|go\.kr)\b"
)
# "kim[at]agency.go.kr", "kim(at)agency.go.kr", "kim 골뱅이 agency.go.kr" — 기호 괄호나 '골뱅이'로
# @만 치환하고 도메인은 정상 표기인 변형. 맨 'at'은 일반 영어("meet at example.com")와
# 구분할 수 없어 괄호가 있는 경우만 잡는다.
EMAIL_BRACKET_PATTERN = (
    r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]++\s*+"
    r"(?:\[\s*(?:at|앳|골뱅이)\s*\]|\(\s*(?:at|앳|골뱅이)\s*\)|골뱅이)\s*+"
    r"[A-Za-z0-9-]++(?:\.[A-Za-z0-9-]++)++(?![A-Za-z0-9-])"
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


def _spelled_digits(raw_match: str) -> tuple[str, bool]:
    """Digits of a mixed Korean-word/real-digit run, and whether any word was spelled out."""
    spelled = any(ch in _KOREAN_DIGIT_VALUES for ch in raw_match)
    digits = "".join(_KOREAN_DIGIT_VALUES.get(ch, ch) for ch in raw_match if ch in _KOREAN_DIGIT_VALUES or ch.isdigit())
    return digits, spelled


def _spells_out_phone(raw_match: str) -> bool:
    digits, spelled = _spelled_digits(raw_match)
    return spelled and bool(re.fullmatch(r"01[016789]\d{7,8}", digits))


def _spells_out_personal_id(raw_match: str) -> bool:
    digits, spelled = _spelled_digits(raw_match)
    return spelled and bool(re.fullmatch(r"\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[1-4]\d{6}", digits))


# Cipher/hash names that follow words like "암호" in ordinary technical prose ("암호는 AES256").
_NON_SECRET_WORDS = re.compile(r"(?i)^(?:aes|sha|rsa|md5|des|3des|tls|ssl|hmac|ecdsa|pbkdf|bcrypt|argon|base64|utf|gcm|cbc|ecb|https?)")


def _looks_like_password_value(raw_match: str) -> bool:
    found = re.search(r"[!-~]{4,}$", raw_match)
    if found is None:
        return False
    value = found.group(0)
    if _NON_SECRET_WORDS.match(value):
        return False
    # A real credential almost always has a digit or symbol; long plain words still count.
    return bool(re.search(r"[0-9!-/:-@\[-`{-~]", value)) or len(value) >= 8


def _looks_like_account_number(raw_match: str) -> bool:
    number = re.search(r"\d{2,6}(?:[- ]\d{2,8}){1,3}$", raw_match)
    if number is None:
        return False
    digits = re.sub(r"\D", "", number.group(0))
    # 10-14 digits; a leading 0 means a phone number (e.g. "부산 051-123-4567"), not an account.
    return 10 <= len(digits) <= 14 and not digits.startswith("0")


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
    _Rule("PERSONAL_ID", "HIGH", PERSONAL_ID_SPELLED_PATTERN, validator=_spells_out_personal_id),
    _Rule("PHONE", "MEDIUM", PHONE_PATTERN),
    _Rule("PHONE", "MEDIUM", PHONE_INTL_PATTERN),
    _Rule("PHONE", "MEDIUM", PHONE_SPELLED_PATTERN, validator=_spells_out_phone),
    _Rule("EMAIL", "MEDIUM", EMAIL_PATTERN),
    _Rule("EMAIL", "MEDIUM", EMAIL_OBFUSCATED_PATTERN),
    _Rule("EMAIL", "MEDIUM", EMAIL_BRACKET_PATTERN),
    _Rule("SECRET", "HIGH", PASSWORD_KO_PATTERN, validator=_looks_like_password_value),
    _Rule("SECRET", "HIGH", PASSWORD_SPELLED_PATTERN),
    _Rule("ACCOUNT_NO", "MEDIUM", ACCOUNT_NO_PATTERN, validator=_looks_like_account_number),
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
