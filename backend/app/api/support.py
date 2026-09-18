import hashlib
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db import get_session_factory
from app.masking import mask_text
from app.models import SupportInquiry, User
from app.security_scan import scan_text


router = APIRouter(prefix="/support", tags=["Support"])

SupportCategory = Literal["HELP", "FILE_FORMAT", "PRIVACY", "FAQ", "INQUIRY", "ERROR", "CONTACT"]


class SupportArticleResponse(BaseModel):
    id: str
    title: str
    description: str


class SupportFaqResponse(BaseModel):
    id: str
    question: str
    answer: str


class PrivacyGuideResponse(BaseModel):
    category: str
    example: str
    caution: str


class SupportContentResponse(BaseModel):
    help: list[SupportArticleResponse]
    faqs: list[SupportFaqResponse]
    privacy: list[PrivacyGuideResponse]
    file_formats: list[str]


class CreateInquiryPayload(BaseModel):
    category: SupportCategory
    subject: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=2000)


class SupportResponse(BaseModel):
    inquiry_id: str
    status: str
    received_at: datetime
    message: str


class InquiryResponse(BaseModel):
    inquiry_id: str
    category: SupportCategory
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    masked_content: str


SUPPORT_CONTENT = SupportContentResponse(
    help=[
        SupportArticleResponse(id="upload", title="문서 업로드", description="문서 업로드 화면에서 파일을 선택한 뒤 서버 검증 상태를 확인합니다."),
        SupportArticleResponse(id="analysis", title="분석 상태", description="분석 Job ID로 접수부터 완료까지의 진행 상태를 다시 조회할 수 있습니다."),
        SupportArticleResponse(id="result", title="C/S/O 및 승인", description="판정 결과에서 등급과 근거를 확인하고, S등급은 권한자 승인 후 진행됩니다."),
        SupportArticleResponse(id="response", title="AI 답변 확인", description="Post-Inspector 검증이 완료된 답변만 화면에 표시됩니다."),
        SupportArticleResponse(id="audit", title="감사·증적", description="Request ID를 기준으로 처리 이력과 메타데이터 중심의 증적을 조회합니다."),
        SupportArticleResponse(id="access", title="권한 기능", description="정책 관리와 운영 현황은 역할과 서버 권한에 따라 제공됩니다."),
    ],
    file_formats=["HWP", "HWPX", "PDF", "PPT", "PPTX", "XLS", "XLSX"],
    privacy=[
        PrivacyGuideResponse(category="개인정보", example="가상의 사용자 식별 정보", caution="개인을 식별할 수 있는 정보는 문의에 입력하지 마세요."),
        PrivacyGuideResponse(category="인증정보", example="비밀번호 또는 인증 토큰", caution="비밀번호, 인증코드, 접근 토큰은 절대 공유하지 마세요."),
        PrivacyGuideResponse(category="금융정보", example="가상의 결제 식별 정보", caution="결제·계좌 관련 정보는 제외하고 현상만 설명하세요."),
        PrivacyGuideResponse(category="계정정보", example="내부 계정 식별자", caution="계정 전체 정보 대신 문제 발생 시각과 Inquiry ID를 사용하세요."),
        PrivacyGuideResponse(category="보안정보", example="보안 설정값", caution="보안 설정의 원문이나 비밀값은 입력하지 마세요."),
        PrivacyGuideResponse(category="기밀정보", example="비공개 업무 내용", caution="업무 원문 대신 마스킹된 요약을 제공하세요."),
        PrivacyGuideResponse(category="기타 민감정보", example="공개가 제한된 자료", caution="민감할 수 있는 자료는 문의에 첨부하거나 복사하지 마세요."),
    ],
    faqs=[
        SupportFaqResponse(id="file", question="어떤 파일을 업로드할 수 있나요?", answer="HWP, HWPX, PDF, PPT, PPTX, XLS, XLSX 형식을 지원합니다. 실제 크기와 개수 제한은 서버 정책을 따릅니다."),
        SupportFaqResponse(id="time", question="분석에는 얼마나 걸리나요?", answer="문서 크기와 대기열 상태에 따라 달라집니다. 분석 화면에서 Job ID와 진행 단계를 확인하세요."),
        SupportFaqResponse(id="grade", question="C/S/O는 무엇인가요?", answer="C는 전송 차단, S는 사람의 승인 필요, O는 정책 검증 완료 상태를 뜻합니다."),
        SupportFaqResponse(id="approval", question="S등급은 왜 승인이 필요한가요?", answer="정책상 검토가 필요한 요청이므로 APPROVER 또는 ADMIN 역할의 승인이 필요합니다."),
        SupportFaqResponse(id="blocked", question="분석 결과가 차단되면 어떻게 하나요?", answer="차단 사유와 탐지 근거를 확인하고 민감정보를 제거하거나 마스킹한 뒤 새 요청을 만드세요."),
        SupportFaqResponse(id="answer", question="AI 답변은 언제 표시되나요?", answer="Post-Inspector 검증이 VERIFIED 상태가 된 뒤에만 표시됩니다."),
        SupportFaqResponse(id="audit", question="Audit/Evidence는 무엇인가요?", answer="Request ID를 기준으로 처리 단계, 승인 이력, 정책 및 증적 메타데이터를 확인하는 기능입니다."),
        SupportFaqResponse(id="inquiry", question="문의 시 어떤 정보를 포함해야 하나요?", answer="문제 발생 시각, Job ID 또는 Request ID, 오류 상태를 포함하세요. 비밀번호·토큰·원문 문서는 포함하지 마세요."),
    ],
)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prepare_inquiry(subject: str, content: str) -> tuple[str, str]:
    combined = f"{subject}\n{content}"
    findings = scan_text(combined)
    if findings:
        categories = ", ".join(sorted({finding.category for finding in findings}))
        raise HTTPException(
            status_code=422,
            detail=f"문의에 민감정보 또는 보안 위험 패턴이 포함되어 있습니다: {categories}",
        )
    masked = mask_text(content).masked_text
    return _hash_text(content), masked


def _inquiry_id(inquiry: SupportInquiry) -> str:
    created = inquiry.created_at or datetime.now(timezone.utc)
    date = created.strftime("%Y%m%d")
    return f"INQ-{date}-{inquiry.id:04d}"


def _parse_inquiry_id(inquiry_id: str) -> int:
    parts = inquiry_id.strip().upper().split("-")
    try:
        parsed = int(parts[-1])
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.") from exc
    if parsed <= 0:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")
    return parsed


def _to_inquiry_response(inquiry: SupportInquiry) -> InquiryResponse:
    return InquiryResponse(
        inquiry_id=_inquiry_id(inquiry),
        category=inquiry.category,
        subject=inquiry.subject,
        status=inquiry.status,
        created_at=inquiry.created_at,
        updated_at=inquiry.updated_at,
        masked_content=inquiry.masked_content,
    )


@router.get("/content", response_model=SupportContentResponse, summary="지원센터 콘텐츠 조회")
def get_support_content(current_user: User = Depends(get_current_user)):
    return SUPPORT_CONTENT


@router.post("/inquiries", response_model=SupportResponse, summary="지원 문의 접수")
def create_inquiry(
    payload: CreateInquiryPayload,
    current_user: User = Depends(get_current_user),
):
    subject = payload.subject.strip()
    content = payload.content.strip()
    if not subject or not content:
        raise HTTPException(status_code=422, detail="문의 제목과 내용을 입력해 주세요.")
    content_hash, masked_content = _prepare_inquiry(subject, content)
    now = datetime.now(timezone.utc)
    session_factory = get_session_factory()
    with session_factory() as db:
        inquiry = SupportInquiry(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            category=payload.category,
            subject=subject,
            content_hash=content_hash,
            masked_content=masked_content,
            status="RECEIVED",
            created_at=now,
            updated_at=now,
        )
        db.add(inquiry)
        db.commit()
        db.refresh(inquiry)
        return SupportResponse(
            inquiry_id=_inquiry_id(inquiry),
            status=inquiry.status,
            received_at=inquiry.created_at,
            message="문의가 접수되었습니다. Inquiry ID를 통해 접수 상태를 확인할 수 있습니다.",
        )


@router.get("/inquiries/{inquiry_id}", response_model=InquiryResponse, summary="지원 문의 상태 조회")
def get_inquiry(
    inquiry_id: str,
    current_user: User = Depends(get_current_user),
):
    session_factory = get_session_factory()
    with session_factory() as db:
        inquiry = db.scalar(
            select(SupportInquiry).where(
                SupportInquiry.id == _parse_inquiry_id(inquiry_id),
                SupportInquiry.tenant_id == current_user.tenant_id,
            )
        )
        if inquiry is None:
            raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")
        return _to_inquiry_response(inquiry)
