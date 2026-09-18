from dataclasses import dataclass
from typing import Protocol

from app.models import SecurityFinding


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


classifier: DocumentClassifier = LocalClassifierAdapter()
