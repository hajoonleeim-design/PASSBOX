# -*- coding: utf-8 -*-
"""
classifier-service 테스트.

실제 파인튜닝된 모델(model_out/)은 CI/로컬 개발 환경에 없을 수 있으므로,
분류 모델 자체(_classify_chunk)는 항상 monkeypatch로 대체한다. 토크나이저는
klue/roberta-base 고정값을 실제로 내려받아 청크 분할 로직만큼은 학습
파이프라인과 동일하게 진짜로 검증한다.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as app_module  # noqa: E402

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def reset_auth_token():
    """테스트 간에 인증 토큰 monkeypatch가 새지 않도록 매번 초기화."""
    original = app_module.AUTH_TOKEN
    yield
    app_module.AUTH_TOKEN = original


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "model_dir" in body


def test_chunk_text_keeps_short_text_as_one_chunk():
    chunks = app_module._chunk_text("짧은 문서입니다.")
    assert chunks == ["짧은 문서입니다."]


def test_chunk_text_splits_long_text_into_multiple_chunks():
    long_text = "이것은 청크 분할 테스트를 위한 문장입니다. " * 300
    chunks = app_module._chunk_text(long_text)
    assert len(chunks) > 1
    for chunk in chunks:
        token_count = len(app_module._tokenizer(chunk, add_special_tokens=False)["input_ids"])
        assert token_count <= app_module.MAX_CHUNK_TOKENS + 5  # 경계 재토큰화 오차 허용


def test_pick_worst_prefers_higher_severity_over_confidence():
    results = [("O", 0.99), ("C", 0.51), ("S", 0.90)]
    grade, confidence = app_module._pick_worst(results)
    assert grade == "C"
    assert confidence == 0.51


def test_pick_worst_breaks_ties_by_confidence():
    results = [("C", 0.60), ("C", 0.95), ("O", 0.99)]
    grade, confidence = app_module._pick_worst(results)
    assert grade == "C"
    assert confidence == 0.95


def test_classify_rejects_missing_auth(monkeypatch):
    app_module.AUTH_TOKEN = "test-secret"
    response = client.post("/classify", json={"text": "hello"})
    assert response.status_code == 401


def test_classify_rejects_wrong_auth(monkeypatch):
    app_module.AUTH_TOKEN = "test-secret"
    response = client.post(
        "/classify", json={"text": "hello"}, headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401


def test_classify_rejects_empty_text(monkeypatch):
    app_module.AUTH_TOKEN = ""
    response = client.post("/classify", json={"text": "   "})
    assert response.status_code == 422


def test_classify_success_with_mocked_model(monkeypatch):
    app_module.AUTH_TOKEN = ""
    monkeypatch.setattr(app_module, "_classify_chunk", lambda chunk: ("S", 0.87))

    response = client.post(
        "/classify",
        json={
            "text": "주민등록번호가 포함된 문서",
            "findings": [{"category": "PERSONAL_ID", "severity": "HIGH", "match_count": 1}],
            "policy_version": "v1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_grade"] == "S"
    assert body["confidence"] == 0.87
    assert body["status"] == "PROVISIONAL"
    assert "PERSONAL_ID" in body["reason"]


def test_classify_multi_chunk_selects_most_severe_grade(monkeypatch):
    app_module.AUTH_TOKEN = ""
    # 청크 3개가 나오도록 충분히 긴 텍스트를 만들고, 두 번째 청크만 C로 응답하게 한다.
    long_text = "일반 업무 안내 문장입니다. " * 300
    monkeypatch.setattr(app_module, "_chunk_text", lambda text: ["첫 구간", "국가핵심기술 유출 구간", "마지막 구간"])

    call_count = {"n": 0}

    def fake_classify(chunk: str):
        call_count["n"] += 1
        if "국가핵심기술" in chunk:
            return ("C", 0.72)
        return ("O", 0.55)

    monkeypatch.setattr(app_module, "_classify_chunk", fake_classify)

    response = client.post("/classify", json={"text": long_text})

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_grade"] == "C"
    assert call_count["n"] == 3
    assert "3개 구간" in body["reason"]
