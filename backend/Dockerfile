# PASSBOX 백엔드 (FastAPI). 빌드 컨텍스트는 backend/ 입니다.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# easyocr(OpenCV)와 PyMuPDF가 쓰는 시스템 라이브러리
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# easyocr가 torch를 끌어오므로 CPU 전용 wheel을 먼저 받아 이미지 크기를 줄인다.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY . .

# 업로드된 파일이 쌓이는 곳. compose가 볼륨으로 연결한다.
RUN mkdir -p /app/storage
EXPOSE 8000

# 테이블이 없으면 만들고(이미 있으면 그대로) 서버를 띄운다.
CMD ["sh", "-c", "python create_tables.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
