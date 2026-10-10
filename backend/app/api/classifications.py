from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.api.auth import get_current_user, require_roles
from app.api.jobs import _update_latest_job_for_document
from app.audit_chain import append_audit_entry
from app.classifier import _GRADE_RANK, ClassifierUnavailableError, apply_confidential_ceiling, apply_findings_floor, classifier
from app.db import Settings, get_session_factory
from app.access import document_access_clause
from app.models import (
    ClassificationRecommendation,
    ClassificationDecision,
    Document,
    DocumentScan,
    DocumentText,
    SecurityFinding,
    User,
)


router = APIRouter(prefix="/documents", tags=["Classification"])


class ClassificationRecommendationResponse(BaseModel):
    recommendation_id: int
    document_id: int
    recommended_grade: str | None
    confidence: float | None
    reason: str
    model_version: str
    status: str
    created_at: datetime


class ConfirmClassificationRequest(BaseModel):
    confirmed_grade: str = Field(pattern="^[CSO]$")
    comment: str | None = Field(default=None, max_length=2000)


class ClassificationDecisionResponse(BaseModel):
    decision_id: int
    document_id: int
    recommendation_id: int | None
    recommended_grade: str | None
    confirmed_grade: str
    comment: str | None
    confirmed_by: int
    created_at: datetime


def _latest_recommendation(db, document_id: int, tenant_id: int):
    return db.scalar(
        select(ClassificationRecommendation)
        .where(
            ClassificationRecommendation.document_id == document_id,
            ClassificationRecommendation.tenant_id == tenant_id,
        )
        .order_by(desc(ClassificationRecommendation.created_at))
    )


def _to_decision_response(
    decision: ClassificationDecision,
    recommendation: ClassificationRecommendation | None,
) -> ClassificationDecisionResponse:
    return ClassificationDecisionResponse(
        decision_id=decision.id,
        document_id=decision.document_id,
        recommendation_id=decision.recommendation_id,
        recommended_grade=recommendation.recommended_grade if recommendation else None,
        confirmed_grade=decision.confirmed_grade,
        comment=decision.comment,
        confirmed_by=decision.user_id,
        created_at=decision.created_at,
    )


def _to_response(
    recommendation: ClassificationRecommendation,
) -> ClassificationRecommendationResponse:
    return ClassificationRecommendationResponse(
        recommendation_id=recommendation.id,
        document_id=recommendation.document_id,
        recommended_grade=recommendation.recommended_grade,
        confidence=recommendation.confidence,
        reason=recommendation.reason,
        model_version=recommendation.model_version,
        status=recommendation.status,
        created_at=recommendation.created_at,
    )


@router.post(
    "/{document_id}/classification/recommend",
    response_model=ClassificationRecommendationResponse,
    summary="문서 보안등급 추천",
    description=(
        "내부 분류기 어댑터를 호출해 C/S/O 후보를 추천합니다. 추천 결과는 최종 확정이 "
        "아니며 담당자 확인 후 사용해야 합니다."
    ),
)
def recommend_classification(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        existing = _latest_recommendation(db, document.id, current_user.tenant_id)
        if existing is not None:
            return _to_response(existing)

        scan = db.scalar(
            select(DocumentScan).where(DocumentScan.document_id == document.id)
        )
        if scan is None or scan.status != "READY_FOR_CLASSIFICATION":
            raise HTTPException(
                status_code=409,
                detail="보안 검사를 통과한 문서만 분류 추천을 요청할 수 있습니다.",
            )

        text_record = db.scalar(
            select(DocumentText).where(DocumentText.document_id == document.id)
        )
        if text_record is None or text_record.status not in {
            "EXTRACTED",
            "EXTRACTED_TRUNCATED",
        }:
            raise HTTPException(status_code=409, detail="먼저 문서 텍스트를 추출해야 합니다.")

        findings = list(
            db.scalars(
                select(SecurityFinding).where(SecurityFinding.scan_id == scan.id)
            )
        )
        try:
            recommendation_result = classifier.recommend(text_record.extracted_text, findings)
        except ClassifierUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"분류 서버를 사용할 수 없습니다. 잠시 후 다시 시도해주세요: {exc}",
            ) from exc
        recommendation_result = apply_confidential_ceiling(recommendation_result, findings, text_record.extracted_text)
        recommendation_result = apply_findings_floor(recommendation_result, findings)
        recommendation = ClassificationRecommendation(
            tenant_id=document.tenant_id,
            document_id=document.id,
            recommended_grade=recommendation_result.recommended_grade,
            confidence=recommendation_result.confidence,
            reason=recommendation_result.reason,
            model_version=recommendation_result.model_version,
            status=recommendation_result.status,
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return _to_response(recommendation)


@router.get(
    "/{document_id}/classification/recommendation",
    response_model=ClassificationRecommendationResponse,
    summary="저장된 분류 추천 조회",
)
def get_classification_recommendation(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        recommendation = _latest_recommendation(db, document.id, current_user.tenant_id)
        if recommendation is None:
            raise HTTPException(status_code=404, detail="분류 추천 결과가 없습니다.")
        return _to_response(recommendation)


@router.get(
    "/{document_id}/source-document",
    summary="분류 확정 전 원본 문서 다운로드",
    description=(
        "OPERATOR, SECURITY_ADMIN 또는 ADMIN 담당자가 C/S/O 등급을 확정하기 전, "
        "판단 근거가 되는 원본 문서를 내려받습니다. 이미 등급이 확정된 문서는 "
        "/approvals/{approval_id}/document 에서 같은 방식으로 확인합니다."
    ),
)
def download_source_document(
    document_id: int,
    current_user: User = Depends(
        require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")
    ),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        storage_root = Path(Settings().storage_root).resolve()
        storage_path = (storage_root / document.storage_key).resolve()
        if storage_root not in storage_path.parents:
            raise HTTPException(status_code=500, detail="Invalid document storage path.")
        if not storage_path.is_file():
            raise HTTPException(status_code=404, detail="저장된 문서 파일을 찾을 수 없습니다.")

        return FileResponse(
            path=storage_path,
            media_type="application/octet-stream",
            filename=Path(document.original_filename).name,
            content_disposition_type="attachment",
            headers={"X-Content-Type-Options": "nosniff"},
        )


@router.get(
    "/{document_id}/classification/decision",
    response_model=ClassificationDecisionResponse,
    summary="저장된 최종 등급 조회",
)
def get_classification_decision(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        decision = db.scalar(
            select(ClassificationDecision)
            .where(
                ClassificationDecision.document_id == document.id,
                ClassificationDecision.tenant_id == current_user.tenant_id,
            )
            .order_by(desc(ClassificationDecision.created_at))
        )
        if decision is None:
            raise HTTPException(status_code=404, detail="최종 확정 결과가 없습니다.")
        recommendation = _latest_recommendation(db, document.id, current_user.tenant_id)
        return _to_decision_response(decision, recommendation)


@router.post(
    "/{document_id}/classification/confirm",
    response_model=ClassificationDecisionResponse,
    summary="문서 C/S/O 등급 최종 확정",
    description=(
        "AI 추천을 참고해 OPERATOR, SECURITY_ADMIN 또는 ADMIN 담당자가 C/S/O 등급을 확정합니다."
    ),
)
def confirm_classification(
    document_id: int,
    payload: ConfirmClassificationRequest,
    current_user: User = Depends(
        require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")
    ),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == current_user.tenant_id,
                document_access_clause(current_user),
            )
        )
        if document is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        if document.status not in {
            "READY_FOR_CLASSIFICATION",
            "CLASSIFICATION_CONFIRMED",
        }:
            raise HTTPException(
                status_code=409,
                detail="보안 검사를 통과한 문서만 등급을 확정할 수 있습니다.",
            )

        recommendation = _latest_recommendation(db, document.id, current_user.tenant_id)
        if recommendation is None:
            raise HTTPException(
                status_code=409,
                detail="먼저 분류 추천을 요청해야 등급을 확정할 수 있습니다.",
            )

        # Separation of duties: confirming your OWN document below the recommended grade
        # (e.g. S -> O) would let one person decide that their own upload may leave unmasked.
        if (
            document.uploaded_by == current_user.id
            and _GRADE_RANK[payload.confirmed_grade] > _GRADE_RANK.get(recommendation.recommended_grade, 2)
        ):
            raise HTTPException(
                status_code=403,
                detail="본인이 올린 문서의 등급을 추천보다 낮게 확정할 수 없습니다. 다른 담당자에게 확정을 요청하세요.",
            )

        decision = ClassificationDecision(
            tenant_id=document.tenant_id,
            document_id=document.id,
            user_id=current_user.id,
            recommendation_id=recommendation.id,
            confirmed_grade=payload.confirmed_grade,
            comment=payload.comment,
        )
        db.add(decision)
        db.flush()
        append_audit_entry(
            db,
            tenant_id=document.tenant_id,
            event_type="CLASSIFICATION_CONFIRMED",
            payload={
                "document_id": document.id,
                "confirmed_grade": decision.confirmed_grade,
                "confirmed_by": current_user.id,
                "recommendation_id": recommendation.id,
            },
        )
        document.status = "CLASSIFICATION_CONFIRMED"
        _update_latest_job_for_document(
            db,
            document_id=document.id,
            tenant_id=current_user.tenant_id,
            status_value="COMPLETED",
            progress=100,
            error_message=None,
        )
        db.commit()
        db.refresh(decision)
        return _to_decision_response(decision, recommendation)
