from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import get_current_user, require_roles
from app.api.jobs import _update_latest_job_for_document
from app.audit_chain import append_audit_entry
from app.db import get_session_factory
from app.models import (
    ClassificationDecision,
    ClassificationRecommendation,
    Document,
    ReviewRequest,
    User,
)


router = APIRouter(prefix="/review-requests", tags=["ReviewRequests"])
REVIEWER_ROLES = ("OPERATOR", "SECURITY_ADMIN", "ADMIN")


class CreateReviewRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    flag_for_retraining: bool = False


class DecideReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: str | None = Field(default=None, max_length=2000)
    new_grade: str | None = Field(default=None, pattern="^[CSO]$")


class ReviewRequestResponse(BaseModel):
    review_request_id: int
    document_id: int
    file_name: str
    original_grade: str
    reason: str
    flag_for_retraining: bool
    status: str
    requested_by: int
    requested_by_name: str
    resolved_by: int | None
    resolution_comment: str | None
    resolved_grade: str | None
    created_at: datetime
    resolved_at: datetime | None


def _latest_decision(db, document_id: int, tenant_id: int) -> ClassificationDecision | None:
    return db.scalar(
        select(ClassificationDecision)
        .where(
            ClassificationDecision.document_id == document_id,
            ClassificationDecision.tenant_id == tenant_id,
        )
        .order_by(desc(ClassificationDecision.created_at))
    )


def _latest_recommendation(db, document_id: int, tenant_id: int) -> ClassificationRecommendation | None:
    return db.scalar(
        select(ClassificationRecommendation)
        .where(
            ClassificationRecommendation.document_id == document_id,
            ClassificationRecommendation.tenant_id == tenant_id,
        )
        .order_by(desc(ClassificationRecommendation.created_at))
    )


def _to_response(item: ReviewRequest, document: Document, requester: User) -> ReviewRequestResponse:
    return ReviewRequestResponse(
        review_request_id=item.id,
        document_id=item.document_id,
        file_name=document.original_filename,
        original_grade=item.original_grade,
        reason=item.reason,
        flag_for_retraining=item.flag_for_retraining,
        status=item.status,
        requested_by=item.requested_by,
        requested_by_name=requester.display_name,
        resolved_by=item.resolved_by,
        resolution_comment=item.resolution_comment,
        resolved_grade=item.resolved_grade,
        created_at=item.created_at,
        resolved_at=item.resolved_at,
    )


@router.post(
    "/documents/{document_id}",
    response_model=ReviewRequestResponse,
    summary="C등급 판정에 대한 재검토 요청 등록",
    description=(
        "외부 전송이 차단된(C등급) 문서에 대해 사용자가 재검토를 요청합니다. "
        "OPERATOR/SECURITY_ADMIN/ADMIN 큐에 등록되며, flag_for_retraining을 "
        "켜면 분류기 재학습 데이터 후보로 함께 표시됩니다."
    ),
)
def create_review_request(
    document_id: int,
    payload: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        decision = _latest_decision(db, document_id, current_user.tenant_id)
        if decision is None:
            raise HTTPException(status_code=409, detail="아직 등급이 확정되지 않은 문서입니다.")
        if decision.confirmed_grade != "C":
            raise HTTPException(
                status_code=409,
                detail="재검토 요청은 외부 전송이 차단된(C등급) 문서에만 등록할 수 있습니다.",
            )

        existing = db.scalar(
            select(ReviewRequest).where(
                ReviewRequest.document_id == document_id,
                ReviewRequest.tenant_id == current_user.tenant_id,
                ReviewRequest.status == "PENDING",
            )
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="이미 처리 대기 중인 재검토 요청이 있습니다.")

        review_request = ReviewRequest(
            tenant_id=current_user.tenant_id,
            document_id=document_id,
            requested_by=current_user.id,
            original_grade=decision.confirmed_grade,
            reason=payload.reason,
            flag_for_retraining=payload.flag_for_retraining,
        )
        db.add(review_request)
        db.flush()
        append_audit_entry(
            db,
            tenant_id=current_user.tenant_id,
            event_type="REVIEW_REQUEST_CREATED",
            payload={
                "review_request_id": review_request.id,
                "document_id": document_id,
                "requested_by": current_user.id,
                "flag_for_retraining": payload.flag_for_retraining,
            },
        )
        db.commit()
        db.refresh(review_request)
        return _to_response(review_request, document, current_user)


@router.get(
    "",
    response_model=list[ReviewRequestResponse],
    summary="대기 중인 재검토 요청 조회",
)
def list_review_requests(
    current_user: User = Depends(require_roles(*REVIEWER_ROLES)),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        items = db.scalars(
            select(ReviewRequest)
            .where(
                ReviewRequest.tenant_id == current_user.tenant_id,
                ReviewRequest.status == "PENDING",
            )
            .order_by(desc(ReviewRequest.created_at))
        ).all()
        if not items:
            return []
        document_ids = {item.document_id for item in items}
        requester_ids = {item.requested_by for item in items}
        documents = {
            doc.id: doc
            for doc in db.scalars(select(Document).where(Document.id.in_(document_ids))).all()
        }
        requesters = {
            user.id: user
            for user in db.scalars(select(User).where(User.id.in_(requester_ids))).all()
        }
        return [
            _to_response(item, documents[item.document_id], requesters[item.requested_by])
            for item in items
        ]


@router.post(
    "/{review_request_id}/decide",
    response_model=ReviewRequestResponse,
    summary="재검토 요청 승인(등급 재조정) 또는 반려",
)
def decide_review_request(
    review_request_id: int,
    payload: DecideReviewRequest,
    current_user: User = Depends(require_roles(*REVIEWER_ROLES)),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        item = db.scalar(
            select(ReviewRequest).where(
                ReviewRequest.id == review_request_id,
                ReviewRequest.tenant_id == current_user.tenant_id,
            ).with_for_update()
        )
        if item is None:
            raise HTTPException(status_code=404, detail="재검토 요청을 찾을 수 없습니다.")
        if item.status != "PENDING":
            raise HTTPException(status_code=409, detail="이미 처리된 재검토 요청입니다.")

        document = db.scalar(select(Document).where(Document.id == item.document_id))
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        now = datetime.now(timezone.utc)
        if payload.action == "approve":
            if payload.new_grade is None:
                raise HTTPException(status_code=422, detail="승인 시 재조정할 등급을 지정해야 합니다.")
            recommendation = _latest_recommendation(db, item.document_id, current_user.tenant_id)
            new_decision = ClassificationDecision(
                tenant_id=current_user.tenant_id,
                document_id=item.document_id,
                user_id=current_user.id,
                recommendation_id=recommendation.id if recommendation else None,
                confirmed_grade=payload.new_grade,
                comment=f"재검토 요청 #{item.id} 승인: {payload.comment or ''}".strip(),
            )
            db.add(new_decision)
            item.status = "APPROVED"
            item.resolved_grade = payload.new_grade
            document.status = "CLASSIFICATION_CONFIRMED"
            _update_latest_job_for_document(
                db,
                document_id=item.document_id,
                tenant_id=current_user.tenant_id,
                status_value="COMPLETED",
                progress=100,
                error_message=None,
            )
        else:
            item.status = "REJECTED"

        item.resolved_by = current_user.id
        item.resolution_comment = payload.comment
        item.resolved_at = now

        append_audit_entry(
            db,
            tenant_id=current_user.tenant_id,
            event_type="REVIEW_REQUEST_DECIDED",
            payload={
                "review_request_id": item.id,
                "document_id": item.document_id,
                "decision": item.status,
                "resolved_grade": item.resolved_grade,
                "resolved_by": current_user.id,
            },
        )
        db.commit()
        db.refresh(item)
        requester = db.scalar(select(User).where(User.id == item.requested_by))
        return _to_response(item, document, requester)
