from contextlib import asynccontextmanager

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
from app.api.decisions import router as decisions_router
from app.api.audit import router as audit_router
from app.api.policies import router as policies_router
from app.api.operations import router as operations_router
from app.api.chat import router as chat_router
from app.api.support import router as support_router
from app.db import Settings, check_database
from app.job_worker import start_worker, stop_worker


def _parse_cors_origins(value: str) -> list[str]:
    origins = list(dict.fromkeys(origin.strip() for origin in value.split(",") if origin.strip()))
    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*'")
    return origins


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_worker()
    try:
        yield
    finally:
        stop_worker()


app = FastAPI(
    title="PASSBOX Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = _parse_cors_origins(Settings().cors_allowed_origins)

# 로컬 프론트엔드 개발용 CORS 설정입니다.
# 운영 배포 시에는 실제 프론트엔드 주소만 남겨야 합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(support_router, prefix="/api/v1")


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
