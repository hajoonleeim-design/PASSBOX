# PASSBOX 분류 추론 서버 (KLUE-RoBERTa). 빌드 컨텍스트는 classifier-service/ 입니다.
# 모델 파일(model_out/, 약 440MB)은 이미지에 넣지 않고 compose가 볼륨으로 연결한다.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY app.py .

ENV CLASSIFIER_MODEL_DIR=/model_out
EXPOSE 8100

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
