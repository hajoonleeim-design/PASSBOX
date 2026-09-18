from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.approvals import router as approvals_router
from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router
from app.api.extraction import router as extraction_router
from app.api.scans import router as scans_router
from app.api.classifications import router as classifications_router
from app.api.outbound import router as outbound_router
from app.api.gateway import router as gateway_router
from app.db import check_database


app = FastAPI(
    title="PASSBOX Backend API",
    version="0.1.0",
)

# 로컬 프론트엔드 개발용 CORS 설정입니다.
# 운영 배포 시에는 실제 프론트엔드 주소만 남겨야 합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(classifications_router, prefix="/api/v1")
app.include_router(outbound_router, prefix="/api/v1")
app.include_router(gateway_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "PASSBOX Backend API",
    }


@app.get("/api/v1/db-check")
def database_check():
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="database connection failed",
        ) from exc

    return {
        "status": "ok",
        "database": "connected",
    }
