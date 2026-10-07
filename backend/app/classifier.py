from dataclasses import dataclass
import json
import logging
from typing import NoReturn, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.db import Settings
from app.models import SecurityFinding


logger = logging.getLogger(__name__)


class ClassifierUnavailableError(Exception):
    """Raised when the remote classifier could not be reached or answered.

    Callers must treat this as a transient failure to retry, never as a
    signal to save a permanent recommendation.
    """


@dataclass(frozen=True)
class ClassificationRecommendation:
    recommended_grade: str | None
    confidence: float | None
    reason: str
    model_version: str
    status: str


class DocumentClassifier(Protocol):
    def recommend(
        self, text: str, findings: list[SecurityFinding]
    ) -> ClassificationRecommendation:
        ...


class LocalClassifierAdapter:
    """교체용 로컬 분류기 어댑터.

    현재는 모델이 아직 없으므로 보안 탐지 결과만 이용한 임시 추천을 반환합니다.
    실제 자체 AI를 붙일 때 이 클래스의 recommend()를 모델 추론 코드로 교체합니다.
    """

    model_version = "local-rules-placeholder-v0"

    def recommend(
        self, text: str, findings: list[SecurityFinding]
    ) -> ClassificationRecommendation:
        high_categories = sorted(
            {finding.category for finding in findings if finding.severity == "HIGH"}
        )
        if high_categories:
            return ClassificationRecommendation(
                recommended_grade="S",
                confidence=0.60,
                reason=(
                    "임시 규칙 기반 추천입니다. 고위험 탐지 유형: "
                    + ", ".join(high_categories)
                ),
                model_version=self.model_version,
                status="PROVISIONAL",
            )

        return ClassificationRecommendation(
            recommended_grade="C",
            confidence=0.40,
            reason=(
                "임시 규칙 기반 추천입니다. 실제 자체 분류 AI 연결 후 결과를 교체하고 "
                "담당자 최종 확인이 필요합니다."
            ),
            model_version=self.model_version,
            status="PROVISIONAL",
        )


class RemoteClassifierAdapter:
    """Call a trusted internal GPU classifier without exposing it to browsers.

    On transport or response errors the adapter raises
    ``ClassifierUnavailableError`` instead of guessing a grade, so callers can
    retry later. It never turns a failed model call into an allow decision.
    """

    def __init__(self, settings: Settings):
        self.url = settings.classifier_service_url.strip()
        self.token = settings.classifier_service_token.strip()
        self.timeout = settings.classifier_timeout_seconds
        self.model_version = settings.classifier_model.strip() or "remote-classifier"
        self.policy_version = settings.classifier_policy_version.strip() or "unknown"

    def recommend(
        self, text: str, findings: list[SecurityFinding]
    ) -> ClassificationRecommendation:
        if not self.url:
            self._unavailable("분류 서버 주소가 설정되지 않았습니다.")

        payload = {
            "text": text,
            "findings": [
                {
                    "category": finding.category,
                    "severity": finding.severity,
                    "match_count": finding.match_count,
                    "line_hint": finding.line_hint,
                }
                for finding in findings
            ],
            "policy_version": self.policy_version,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib_request.Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib_error.URLError, json.JSONDecodeError) as exc:
            self._unavailable(f"분류 서버 응답을 확인하지 못했습니다: {exc}")

        if not isinstance(body, dict):
            self._unavailable("분류 서버 응답 형식이 올바르지 않습니다.")

        grade = body.get("recommended_grade")
        if grade not in {None, "C", "S", "O"}:
            self._unavailable(f"분류 서버가 올바르지 않은 등급을 반환했습니다: {grade!r}")

        confidence = body.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            confidence = None

        reason = str(body.get("reason") or "담당자의 최종 검토가 필요합니다.")[:1000]
        status = str(body.get("status") or ("PROVISIONAL" if grade else "REVIEW_REQUIRED"))
        model_version = str(body.get("model_version") or self.model_version)[:120]
        return ClassificationRecommendation(
            recommended_grade=grade,
            confidence=float(confidence) if confidence is not None else None,
            reason=reason,
            model_version=model_version,
            status=status,
        )

    def _unavailable(self, reason: str) -> NoReturn:
        logger.warning("원격 분류 서버 호출 실패: %s", reason)
        raise ClassifierUnavailableError(reason)


# C > S > O. Used only to decide whether a floor grade is an upgrade, never
# to downgrade a model's own (possibly stricter) recommendation.
_GRADE_RANK = {"C": 0, "S": 1, "O": 2}

# Severities whose regex findings (security_scan.py) mean the document
# contains PII/secret-shaped text, regardless of what the model's own
# chunk-level judgment concluded about surrounding context.
_FLOOR_SEVERITIES = {"HIGH", "MEDIUM"}


def apply_findings_floor(
    result: ClassificationRecommendation, findings: list[SecurityFinding]
) -> ClassificationRecommendation:
    """Never let a regex-confirmed PII/secret hit get recommended as O.

    The classifier judges a whole chunk's *context* and can decide a stray
    phone-number-shaped string "looks like a placeholder" and grade the
    chunk O. But regex detection can't tell a placeholder from a real
    number, and this is a security system: a false negative here (real PII
    leaving as O) is far worse than a false positive (a placeholder getting
    S and needing one extra approval click). So any HIGH/MEDIUM finding
    sets a floor of S on the recommendation — it can only raise the grade
    (or leave a C alone), never lower it.

    Both call sites that produce a saved ClassificationRecommendation (the
    job pipeline's auto-recommendation and the on-demand recommend
    endpoint) must route through this, or the floor silently stops applying
    to whichever path skips it.
    """
    floor_categories = sorted(
        {f.category for f in findings if f.severity in _FLOOR_SEVERITIES}
    )
    if not floor_categories:
        return result

    current_rank = _GRADE_RANK.get(result.recommended_grade, _GRADE_RANK["O"] + 1)
    if current_rank <= _GRADE_RANK["S"]:
        return result

    note = (
        " [자동 보정] 모델 추천은 "
        f"{result.recommended_grade or '없음'}이었지만, 탐지된 개인정보/Secret 유형("
        + ", ".join(floor_categories)
        + ")이 있어 S 미만으로 내려가지 않도록 등급을 올렸습니다."
    )
    return ClassificationRecommendation(
        recommended_grade="S",
        confidence=result.confidence,
        reason=result.reason + note,
        model_version=result.model_version,
        status=result.status,
    )


def build_classifier(settings: Settings | None = None) -> DocumentClassifier:
    runtime_settings = settings or Settings()
    if runtime_settings.classifier_mode.strip().upper() == "REMOTE":
        return RemoteClassifierAdapter(runtime_settings)
    return LocalClassifierAdapter()


classifier: DocumentClassifier = build_classifier()
