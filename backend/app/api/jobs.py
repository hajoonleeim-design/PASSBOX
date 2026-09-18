from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.api.auth import get_current_user
from app.db import get_session_factory
from app.models import Document, Job, Request as AnalysisRequest, User


router = APIRouter(prefix="/jobs", tags=["Jobs"])


class CreateJobRequest(BaseModel):
    document_id: int


class JobResponse(BaseModel):
    job_id: int
    request_id: int
    document_id: int
    file_name: str
    extension: str
    size: int
    status: str
    current_step: str
    progress: int
    created_at: datetime
    updated_at: datetime
    can_cancel: bool
    failure_message: str | None = None


def _to_response(job: Job, request: AnalysisRequest, document: Document) -> JobResponse:
    # 프론트엔드의 현재 상태 모델과 맞추기 위해 DB의 QUEUED를 접수 단계로 표시합니다.
    display_status = "RECEIVED" if job.status == "QUEUED" else job.status
    current_step = "분석 대기" if job.status == "QUEUED" else job.status
    return JobResponse(
        job_id=job.id,
        request_id=request.id,
        document_id=document.id,
        file_name=document.original_filename,
        extension=document.extension,
        size=document.size_bytes,
        status=display_status,
        current_step=current_step,
        progress=job.progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
        can_cancel=job.status in {"QUEUED", "RECEIVED", "INSPECTING", "PARSING"},
        failure_message=job.error_message,
    )


def _find_job(db, job_id: int, tenant_id: int):
    return db.execute(
        select(Job, AnalysisRequest, Document)
        .join(AnalysisRequest, Job.request_id == AnalysisRequest.id)
        .join(Document, AnalysisRequest.document_id == Document.id)
        .where(
            Job.id == job_id,
            AnalysisRequest.tenant_id == tenant_id,
        )
    ).first()


def _update_latest_job_for_document(
    db,
    *,
    document_id: int,
    tenant_id: int,
    status_value: str,
    progress: int,
    error_message: str | None = None,
):
    result = db.execute(
        select(Job, AnalysisRequest)
        .join(AnalysisRequest, Job.request_id == AnalysisRequest.id)
        .where(
            AnalysisRequest.document_id == document_id,
            AnalysisRequest.tenant_id == tenant_id,
        )
        .order_by(desc(Job.created_at))
    ).first()
    if result is None:
        return None
    job, request = result
    job.status = status_value
    job.progress = progress
    job.error_message = error_message
    job.updated_at = datetime.now(timezone.utc)
    request.status = status_value
    return job


def _reset_failed_job(job: Job, request: AnalysisRequest) -> None:
    if job.status != "FAILED":
        raise HTTPException(
            status_code=409,
            detail="실패한 Job만 다시 시도할 수 있습니다.",
        )
    job.status = "QUEUED"
    job.progress = 0
    job.error_message = None
    job.updated_at = datetime.now(timezone.utc)
    request.status = "RECEIVED"


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="문서 분석 Job 생성",
)
def create_job(
    payload: CreateJobRequest,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == payload.document_id,
                Document.tenant_id == current_user.tenant_id,
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        if document.status not in {"READY_FOR_CLASSIFICATION", "CLASSIFICATION_CONFIRMED"}:
            raise HTTPException(
                status_code=409,
                detail=f"분석을 시작할 수 없는 문서 상태입니다: {document.status}",
            )

        request = AnalysisRequest(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            document_id=document.id,
            mode="DOCUMENT",
            status="RECEIVED",
        )
        db.add(request)
        db.flush()

        job = Job(
            request_id=request.id,
            status="QUEUED",
            progress=0,
            error_message=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        db.refresh(request)

        return _to_response(job, request, document)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="분석 Job 상태 조회",
)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        result = _find_job(db, job_id, current_user.tenant_id)
        if result is None:
            raise HTTPException(status_code=404, detail="분석 Job을 찾을 수 없습니다.")
        job, request, document = result
        return _to_response(job, request, document)


@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
    summary="분석 Job 취소",
)
def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        result = _find_job(db, job_id, current_user.tenant_id)
        if result is None:
            raise HTTPException(status_code=404, detail="분석 Job을 찾을 수 없습니다.")
        job, request, document = result
        if job.status not in {"QUEUED", "RECEIVED", "INSPECTING", "PARSING"}:
            raise HTTPException(status_code=409, detail="현재 상태에서는 Job을 취소할 수 없습니다.")

        job.status = "CANCELLED"
        job.updated_at = datetime.now(timezone.utc)
        request.status = "CANCELLED"
        db.commit()
        db.refresh(job)
        return _to_response(job, request, document)


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="실패한 분석 Job 재시도",
)
def retry_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        result = _find_job(db, job_id, current_user.tenant_id)
        if result is None:
            raise HTTPException(status_code=404, detail="분석 Job을 찾을 수 없습니다.")
        job, request, document = result
        _reset_failed_job(job, request)
        db.commit()
        db.refresh(job)
        db.refresh(request)
        return _to_response(job, request, document)
