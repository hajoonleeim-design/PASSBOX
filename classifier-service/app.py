# -*- coding: utf-8 -*-
"""
PASSBOX 분류 추론 서버

backend/app/classifier.py의 RemoteClassifierAdapter가 호출하는 계약을
그대로 구현한다.

  요청  POST /classify
        {"text": str, "findings": [...], "policy_version": str}

  응답  {"recommended_grade": "C"|"S"|"O", "confidence": float,
         "reason": str, "model_version": str, "status": "PROVISIONAL"}

512토큰을 넘는 문서는 학습 때(chunk_corpus.py)와 동일한 방식으로 청크
분할한 뒤, 국정원 N2SF 표 2-9(혼재 시 최고등급) 원칙에 따라 C > S > O
순으로 가장 심각한 청크의 판정을 문서 전체 판정으로 채택한다.

토크나이저(klue/roberta-base)는 항상 고정이라 즉시 로드하지만, 실제
파인튜닝된 분류 모델(MODEL_DIR)은 첫 분류 요청이 들어올 때 지연 로드한다
— 그래야 모델 파일이 없는 개발/CI 환경에서도 청크 분할 로직 등을
모델 없이 테스트할 수 있다.
"""

from __future__ import annotations

import os
from pathlib import Path

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

TOKENIZER_NAME = "klue/roberta-base"  # 학습 파이프라인과 항상 동일해야 함
MODEL_DIR = os.environ.get("CLASSIFIER_MODEL_DIR", "./model_out")
AUTH_TOKEN = os.environ.get("CLASSIFIER_AUTH_TOKEN", "").strip()
MAX_CHUNK_TOKENS = 490
MIN_TAIL_TOKENS = 200  # 이보다 짧은 마지막 조각은 문맥이 끊겨 오분류되기 쉬워 직전 조각에 합친다
# 표 2-9: 혼재 시 최고등급 우선. 숫자가 작을수록 심각하다.
GRADE_SEVERITY = {"C": 0, "S": 1, "O": 2}

app = FastAPI(title="PASSBOX Classifier Service")

_tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = None  # 지연 로드


def _get_model():
    global _model
    if _model is None:
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(_device)
        _model.eval()
    return _model


class Finding(BaseModel):
    category: str
    severity: str
    match_count: int
    line_hint: int | None = None


class ClassifyRequest(BaseModel):
    text: str
    findings: list[Finding] = []
    policy_version: str = ""


class ClassifyResponse(BaseModel):
    recommended_grade: str | None
    confidence: float | None
    reason: str
    model_version: str
    status: str


def _chunk_text(text: str) -> list[str]:
    """chunk_corpus.py와 동일한 오프셋 기반 분할(디코딩 왜곡 없음)."""
    encoding = _tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
    offsets = [o for o in encoding["offset_mapping"] if o != (0, 0)]
    total = len(offsets)
    if total <= MAX_CHUNK_TOKENS:
        return [text]

    boundaries = list(range(0, total, MAX_CHUNK_TOKENS))  # 각 구간의 시작 토큰 인덱스

    # 마지막 조각이 짧으면 앞뒤 문맥 없이 단어 몇 개만 남아 모델이 헷갈리기 쉽다.
    # (예: "중요 문서(C/S)의 외부 AI 유출을 원천 차단" 같은 조각만 떼어놓으면
    # 실제로는 공개 문서인데도 보안 관련 단어만 보고 S로 오판하는 사례를 확인했다.)
    # 단순히 직전 조각에 이어붙이면 합친 길이가 MAX_CHUNK_TOKENS를 넘어 모델의
    # max_length=512 절단에 걸려 오히려 방금 붙인 꼬리 부분이 잘려나간다.
    # 그래서 마지막 두 조각을 절반씩 재분배해 둘 다 MAX_CHUNK_TOKENS 이내로 유지한다.
    if len(boundaries) > 1:
        last_start = boundaries[-1]
        tail_len = total - last_start
        if tail_len < MIN_TAIL_TOKENS:
            merge_start = boundaries[-2]
            half = (total - merge_start) // 2
            boundaries = boundaries[:-2] + [merge_start, merge_start + half]

    windows: list[tuple[int, int]] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else total
        windows.append((offsets[start][0], offsets[end - 1][1]))

    chunks: list[str] = []
    for char_start, char_end in windows:
        piece = text[char_start:char_end].strip()
        if piece:
            chunks.append(piece)
    return chunks or [text]


@torch.inference_mode()
def _classify_chunk(chunk: str) -> tuple[str, float]:
    model = _get_model()
    inputs = _tokenizer(chunk, truncation=True, max_length=512, return_tensors="pt").to(_device)
    logits = model(**inputs).logits[0]
    probs = torch.softmax(logits, dim=-1)
    top_id = int(torch.argmax(probs).item())
    return model.config.id2label[top_id], float(probs[top_id].item())


def _pick_worst(results: list[tuple[str, float]]) -> tuple[str, float]:
    """표 2-9: 혼재 시 최고등급(C > S > O). 동률이면 확신도가 높은 쪽."""
    return min(results, key=lambda r: (GRADE_SEVERITY[r[0]], -r[1]))


def _check_auth(authorization: str | None) -> None:
    if not AUTH_TOKEN:
        return
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="인증 토큰이 올바르지 않습니다.")


@app.post("/classify", response_model=ClassifyResponse)
def classify(payload: ClassifyRequest, authorization: str | None = Header(default=None)):
    _check_auth(authorization)

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="분류할 텍스트가 없습니다.")

    chunks = _chunk_text(text)
    results = [_classify_chunk(c) for c in chunks]
    best_grade, best_conf = _pick_worst(results)

    finding_note = ""
    if payload.findings:
        categories = sorted({f.category for f in payload.findings})
        finding_note = f" 보안 탐지 유형: {', '.join(categories)}."

    reason = (
        f"KLUE-RoBERTa 분류 모델이 문서를 {len(chunks)}개 구간으로 나눠 평가한 결과, "
        f"최고 등급 {best_grade}로 판단했습니다 (확신도 {best_conf:.2f})." + finding_note
    )

    return ClassifyResponse(
        recommended_grade=best_grade,
        confidence=round(best_conf, 4),
        reason=reason,
        model_version=f"klue-roberta-base-{Path(MODEL_DIR).name}",
        status="PROVISIONAL",
    )


@app.get("/health")
def health():
    return {"status": "ok", "device": _device, "model_dir": str(MODEL_DIR), "model_loaded": _model is not None}
