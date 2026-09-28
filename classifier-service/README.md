# PASSBOX Classifier Service

`backend/app/classifier.py`의 `RemoteClassifierAdapter`가 호출하는 추론 서버입니다.
팀원이 GPU에서 학습해 만든 `model_out/` 폴더(KLUE-RoBERTa 기반, C/S/O 3-class)를
그대로 받아서 HTTP로 서빙합니다.

## 실행

```bash
pip install -r requirements.txt

# model_out 폴더를 이 프로젝트 옆에 두거나 경로를 지정
export CLASSIFIER_MODEL_DIR=./model_out
export CLASSIFIER_AUTH_TOKEN=<임의의 긴 비밀 문자열>   # PASSBOX 쪽 CLASSIFIER_SERVICE_TOKEN과 동일하게

python -m uvicorn app:app --host 0.0.0.0 --port 8100
```

GPU가 있으면 자동으로 사용합니다(`torch.cuda.is_available()`).

## PASSBOX 백엔드 연결

`backend/.env`에서:

```
CLASSIFIER_MODE=REMOTE
CLASSIFIER_SERVICE_URL=http://<이 서버 주소>:8100/classify
CLASSIFIER_SERVICE_TOKEN=<위와 동일한 값>
```

production에서는 `CLASSIFIER_SERVICE_URL`이 반드시 `https://`여야 합니다
(`app/main.py`의 운영 설정 검증에서 강제).

## 동작 방식

- 512토큰이 넘는 문서는 학습 때(`chunk_corpus.py`)와 동일한 방식으로 청크 분할
- 각 청크를 모델로 분류한 뒤, 국정원 N2SF 표 2-9(혼재 시 최고등급) 원칙에 따라
  C > S > O 순으로 가장 심각한 청크의 판정을 문서 전체 판정으로 채택
- 인증 토큰이 다르면 401, 응답 형식이 어긋나면 `RemoteClassifierAdapter`가
  `ClassifierUnavailableError`로 처리해 Job을 재시도 가능한 실패로 표시함

## 검증 상태

`app.py`는 실제 requirements.txt 있는 이 프로젝트에서, 임의 초기화된 동일 구조의
더미 3-class 모델로 엔드투엔드 테스트 완료(인증 거부/통과, 정상 응답 스키마,
긴 문서 청크 분할까지 확인). 실제 학습된 모델로 교체하면 그대로 동작합니다.
