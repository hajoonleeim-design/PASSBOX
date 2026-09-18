from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.api.auth import require_roles
from app.db import get_session_factory
from app.models import (
    ClassificationDecision,
    Document,
    GatewayTransmission,
    Job,
    OutboundApproval,
    Request as AnalysisRequest,
    SecurityPolicy,
    User,
)


router = APIRouter(prefix="/operations", tags=["Operations"])


class OperationsSummaryResponse(BaseModel):
    totalRequests: int
    completedRequests: int
    blockedRequests: int
    failedRequests: int
    processingRequests: int
    successRate: float
    failureRate: float


class QueueStatusResponse(BaseModel):
    totalQueued: int
    received: int
    inspecting: int
    parsing: int
    detecting: int
    masking: int
    waitingApproval: int
    transmitting: int
    postInspecting: int


class OperationsPerformanceResponse(BaseModel):
    averageProcessingTimeMs: int
    p95ProcessingTimeMs: int
    throughputPerHour: int


class ProviderStatusResponse(BaseModel):
    providerId: str
    providerName: str
    status: str
    responseTimeMs: int | None
    lastCheckedAt: datetime
    message: str


class RecentOperationsJobResponse(BaseModel):
    jobId: str
    requestId: str
    fileNameDisplay: str
    status: str
    currentStep: str
    grade: str
    startedAt: datetime
    updatedAt: datetime
    processingTimeMs: int | None


class OperationsIncidentResponse(BaseModel):
    incidentId: str
    severity: str
    status: str
    occurredAt: datetime
    summary: str
    relatedJobId: str | None = None
    resolvedAt: datetime | None = None


class CsoDistributionResponse(BaseModel):
    grade: str
    count: int


class OperationsDashboardResponse(BaseModel):
    generatedAt: datetime
    summary: OperationsSummaryResponse
    queue: QueueStatusResponse
    performance: OperationsPerformanceResponse
    providers: list[ProviderStatusResponse]
    recentJobs: list[RecentOperationsJobResponse]
    csoDistribution: list[CsoDistributionResponse]
    incidents: list[OperationsIncidentResponse]


_TERMINAL_JOB_STATUSES = {"COMPLETED", "BLOCKED", "FAILED", "CANCELLED"}
_QUEUE_KEYS = (
    "received",
    "inspecting",
    "parsing",
    "detecting",
    "masking",
    "waitingApproval",
    "transmitting",
    "postInspecting",
)


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _latest_by(items, key):
    latest = {}
    for item in items:
        item_key = key(item)
        if item_key is None:
            continue
        current = latest.get(item_key)
        if current is None or _timestamp(item.created_at) > _timestamp(current.created_at):
            latest[item_key] = item
    return latest


def _duration_ms(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    duration = max(0.0, (_timestamp(end) - _timestamp(start)) * 1000)
    return int(round(duration))


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return ordered[index]


def _job_display_status(status: str) -> str:
    return "RECEIVED" if status == "QUEUED" else status


def _current_step(status: str) -> str:
    return {
        "QUEUED": "분석 대기",
        "RECEIVED": "접수",
        "INSPECTING": "안전 검사",
        "PARSING": "텍스트 추출",
        "DETECTING": "민감정보 탐지",
        "MASKING": "마스킹",
        "WAITING_APPROVAL": "승인 대기",
        "TRANSMITTING": "Gateway 전송",
        "POST_INSPECTING": "답변 검사",
        "COMPLETED": "완료",
        "BLOCKED": "차단",
        "FAILED": "실패",
        "CANCELLED": "취소",
    }.get(status, status)


def _request_state(
    request: AnalysisRequest,
    job: Job | None,
    transmission: GatewayTransmission | None,
    decision: ClassificationDecision | None,
) -> str:
    if transmission is not None:
        if transmission.status == "COMPLETED":
            return "COMPLETED"
        if transmission.status in {"BLOCKED", "PROMPT_BLOCKED"} or transmission.policy_decision in {
            "BLOCKED",
            "PROMPT_BLOCKED",
        }:
            return "BLOCKED"
        if transmission.status == "FAILED":
            return "FAILED"
        if transmission.status == "WAITING_APPROVAL":
            return "WAITING_APPROVAL"

    # C등급은 전송하지 않는 것이 정상적인 보안 정책 동작이므로 차단으로 집계합니다.
    if decision is not None and decision.confirmed_grade == "C":
        return "BLOCKED"
    if job is not None and job.status in _TERMINAL_JOB_STATUSES:
        return job.status
    if request.status == "CANCELLED":
        return "CANCELLED"
    return job.status if job is not None else request.status


def _queue_bucket(
    job: Job | None,
    transmission: GatewayTransmission | None,
    approval: OutboundApproval | None,
) -> str | None:
    if approval is not None and approval.status == "PENDING":
        return "waitingApproval"
    if transmission is not None:
        if transmission.status == "WAITING_APPROVAL":
            return "waitingApproval"
        if transmission.status in {"QUEUED", "TRANSMITTING"}:
            return "transmitting"
        if transmission.status == "POST_INSPECTING":
            return "postInspecting"
    if job is None or job.status in _TERMINAL_JOB_STATUSES:
        return None
    return {
        "QUEUED": "received",
        "RECEIVED": "received",
        "INSPECTING": "inspecting",
        "PARSING": "parsing",
        "DETECTING": "detecting",
        "MASKING": "masking",
        "WAITING_APPROVAL": "waitingApproval",
        "TRANSMITTING": "transmitting",
        "POST_INSPECTING": "postInspecting",
    }.get(job.status)


def _provider_status(transmission: GatewayTransmission) -> tuple[str, str]:
    if transmission.status == "FAILED":
        return "DOWN", transmission.error_message or "최근 Gateway 호출이 실패했습니다."
    if transmission.status in {"QUEUED", "WAITING_APPROVAL", "TRANSMITTING"}:
        return "DEGRADED", "처리 중인 요청이 있습니다."
    return "HEALTHY", "최근 요청이 정상적으로 처리되었습니다."


def _dashboard_response(
    requests: list[AnalysisRequest],
    jobs: list[Job],
    documents: list[Document],
    decisions: list[ClassificationDecision],
    transmissions: list[GatewayTransmission],
    approvals: list[OutboundApproval],
    policy: SecurityPolicy | None,
    now: datetime,
) -> OperationsDashboardResponse:
    request_by_id = {item.id: item for item in requests}
    document_by_id = {item.id: item for item in documents}
    job_by_request = _latest_by(jobs, lambda item: item.request_id)
    decision_by_document = _latest_by(decisions, lambda item: item.document_id)
    transmission_by_document = _latest_by(transmissions, lambda item: item.document_id)
    approval_by_transmission = _latest_by(approvals, lambda item: item.gateway_transmission_id)

    states = [
        _request_state(
            request,
            job_by_request.get(request.id),
            transmission_by_document.get(request.document_id),
            decision_by_document.get(request.document_id),
        )
        for request in requests
    ]
    completed = states.count("COMPLETED")
    blocked = states.count("BLOCKED")
    failed = states.count("FAILED") + states.count("CANCELLED")
    total = len(requests)
    processing = total - completed - blocked - failed

    queue_counts = {key: 0 for key in _QUEUE_KEYS}
    for request in requests:
        transmission = transmission_by_document.get(request.document_id)
        approval = (
            approval_by_transmission.get(transmission.id)
            if transmission is not None
            else None
        )
        bucket = _queue_bucket(job_by_request.get(request.id), transmission, approval)
        if bucket in queue_counts:
            queue_counts[bucket] += 1

    processing_times = [
        duration
        for job in jobs
        if job.status in _TERMINAL_JOB_STATUSES
        for duration in [_duration_ms(job.created_at, job.updated_at)]
        if duration is not None
    ]
    completed_last_hour = sum(
        1
        for transmission in transmissions
        if transmission.status == "COMPLETED"
        and _timestamp(transmission.created_at) >= _timestamp(now - timedelta(hours=1))
    )

    recent_jobs: list[RecentOperationsJobResponse] = []
    for job in sorted(jobs, key=lambda item: _timestamp(item.updated_at), reverse=True)[:10]:
        request = request_by_id.get(job.request_id)
        if request is None:
            continue
        document = document_by_id.get(request.document_id)
        transmission = transmission_by_document.get(request.document_id)
        decision = decision_by_document.get(request.document_id)
        state = _request_state(request, job, transmission, decision)
        recent_jobs.append(
            RecentOperationsJobResponse(
                jobId=f"JOB-{job.id}",
                requestId=f"REQ-{request.id}",
                fileNameDisplay=document.original_filename if document else "문서 없음",
                status=_job_display_status(state),
                currentStep=_current_step(state),
                grade=decision.confirmed_grade if decision else "O",
                startedAt=job.created_at,
                updatedAt=job.updated_at,
                processingTimeMs=_duration_ms(job.created_at, job.updated_at)
                if state in _TERMINAL_JOB_STATUSES | {"COMPLETED", "BLOCKED"}
                else None,
            )
        )

    cso_counts = defaultdict(int)
    for decision in decision_by_document.values():
        if decision.confirmed_grade in {"C", "S", "O"}:
            cso_counts[decision.confirmed_grade] += 1

    latest_provider = _latest_by(transmissions, lambda item: item.provider)
    provider_names = set(latest_provider)
    if policy is not None:
        provider_names.update(
            str(item.get("provider"))
            for item in (policy.model_allowlist or [])
            if item.get("enabled") and item.get("provider")
        )
    providers: list[ProviderStatusResponse] = []
    for provider in sorted(provider_names):
        transmission = latest_provider.get(provider)
        if transmission is None:
            providers.append(
                ProviderStatusResponse(
                    providerId=provider,
                    providerName=provider,
                    status="UNKNOWN",
                    responseTimeMs=None,
                    lastCheckedAt=now,
                    message="아직 확인된 Gateway 요청이 없습니다.",
                )
            )
            continue
        provider_status, message = _provider_status(transmission)
        providers.append(
            ProviderStatusResponse(
                providerId=provider,
                providerName=provider,
                status=provider_status,
                responseTimeMs=None,
                lastCheckedAt=transmission.created_at,
                message=message,
            )
        )

    job_by_document = {
        request.document_id: job
        for job in jobs
        if (request := request_by_id.get(job.request_id)) is not None
    }
    incidents = [
        OperationsIncidentResponse(
            incidentId=f"INC-TRANSMISSION-{transmission.id}",
            severity="HIGH",
            status="OPEN",
            occurredAt=transmission.created_at,
            summary=transmission.error_message or "Gateway 호출에 실패했습니다.",
            relatedJobId=(
                f"JOB-{job_by_document[transmission.document_id].id}"
                if transmission.document_id in job_by_document
                else None
            ),
        )
        for transmission in sorted(
            (item for item in transmissions if item.status == "FAILED"),
            key=lambda item: _timestamp(item.created_at),
            reverse=True,
        )[:10]
    ]

    success_rate = round(completed / total * 100, 1) if total else 0.0
    failure_rate = round(failed / total * 100, 1) if total else 0.0
    queue_total = sum(queue_counts.values())
    return OperationsDashboardResponse(
        generatedAt=now,
        summary=OperationsSummaryResponse(
            totalRequests=total,
            completedRequests=completed,
            blockedRequests=blocked,
            failedRequests=failed,
            processingRequests=max(0, processing),
            successRate=success_rate,
            failureRate=failure_rate,
        ),
        queue=QueueStatusResponse(totalQueued=queue_total, **queue_counts),
        performance=OperationsPerformanceResponse(
            averageProcessingTimeMs=(
                int(round(sum(processing_times) / len(processing_times)))
                if processing_times
                else 0
            ),
            p95ProcessingTimeMs=_p95(processing_times),
            throughputPerHour=completed_last_hour,
        ),
        providers=providers,
        recentJobs=recent_jobs,
        csoDistribution=[
            CsoDistributionResponse(grade=grade, count=cso_counts[grade])
            for grade in ("C", "S", "O")
        ],
        incidents=incidents,
    )


@router.get(
    "/dashboard",
    response_model=OperationsDashboardResponse,
    summary="운영 대시보드 집계 조회",
)
def get_operations_dashboard(
    current_user: User = Depends(require_roles("ADMIN", "OPERATOR")),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        tenant_id = current_user.tenant_id
        requests = list(
            db.scalars(
                select(AnalysisRequest)
                .where(AnalysisRequest.tenant_id == tenant_id)
                .order_by(desc(AnalysisRequest.created_at))
            ).all()
        )
        jobs = list(
            db.scalars(
                select(Job)
                .join(AnalysisRequest, Job.request_id == AnalysisRequest.id)
                .where(AnalysisRequest.tenant_id == tenant_id)
                .order_by(desc(Job.updated_at))
            ).all()
        )
        documents = list(
            db.scalars(
                select(Document)
                .where(Document.tenant_id == tenant_id)
            ).all()
        )
        decisions = list(
            db.scalars(
                select(ClassificationDecision)
                .where(ClassificationDecision.tenant_id == tenant_id)
            ).all()
        )
        transmissions = list(
            db.scalars(
                select(GatewayTransmission)
                .where(GatewayTransmission.tenant_id == tenant_id)
            ).all()
        )
        approvals = list(
            db.scalars(
                select(OutboundApproval)
                .where(OutboundApproval.tenant_id == tenant_id)
            ).all()
        )
        policy = db.scalar(
            select(SecurityPolicy).where(
                SecurityPolicy.tenant_id == tenant_id,
                SecurityPolicy.status == "ACTIVE",
            )
        )
        return _dashboard_response(
            requests=requests,
            jobs=jobs,
            documents=documents,
            decisions=decisions,
            transmissions=transmissions,
            approvals=approvals,
            policy=policy,
            now=datetime.now(timezone.utc),
        )
