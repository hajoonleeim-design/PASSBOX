# -*- coding: utf-8 -*-
"""
실제 학습된 분류 모델(model_out/)을 대상으로 한 회귀 테스트.

test_app.py와 달리 여기서는 모델을 monkeypatch로 대체하지 않고 진짜로
추론한다. model_out/model.safetensors가 없는 환경(CI, 모델 파일 없는
로컬)에서는 전부 자동으로 skip된다 — 모델이 있는 개발 환경에서
"pytest tests/test_classification_regression.py"로 직접 돌려서 확인한다.

새 모델(v4, v5, ...)을 model_out/에 넣을 때마다 이 파일을 돌려서
과거에 찾았던 오탐 패턴이 재발하지 않는지 확인한다.

문서 텍스트는 실제 PASSBOX 프로젝트의 공개 산출물(작품설명서.docx,
제안 발표자료.pptx)에서 그대로 추출한 진짜 텍스트다. v1 모델이 이 두
문서를 전부 S로 오분류했던 실제 사례이고, v2에서 바이라인 트랩 케이스
추가 + 청킹 재분배 수정으로 고쳐졌다.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as app_module  # noqa: E402

MODEL_PRESENT = (Path(app_module.MODEL_DIR) / "model.safetensors").exists()
pytestmark = pytest.mark.skipif(
    not MODEL_PRESENT,
    reason="실제 학습된 모델(model_out/model.safetensors)이 없어 회귀 테스트를 건너뜁니다.",
)

client = TestClient(app_module.app)


def classify(text: str) -> dict:
    response = client.post(
        "/classify",
        json={"text": text, "findings": [], "policy_version": "regression-test"},
    )
    assert response.status_code == 200, response.text
    return response.json()


WORK_DESCRIPTION_DOCX_TEXT = """[양식 2] 작품설명서
캡스톤 프로젝트 작품 설명서
프로젝트 작품명\tPASSBOX (N2SF with AI)\tPASSBOX (N2SF with AI)\tPASSBOX (N2SF with AI)
소속캠퍼스\t대전캠퍼스\t학  과\t클라우드보안과
성    명\t윤상훈, 이하준, 이학민\t과  정\t하이테크과정
제 작 목 적
○ 국정원 '국가 망 보안체계(N2SF) 가이드라인 1.0' 기반의 데이터 중요도별 차등 보안 통제 체계 구축
○ 기존 획일적 망분리를 탈피하여 공공 업무에서 외부 상용 AI(ChatGPT, Gemini 등)를 안전하게 활용할 수 있는 환경 구현
○ 공공 문서(HWPX/HWP/PDF)의 C·S·O 등급 자동 분류를 통해 기밀 유출 방지 및 상용 AI 연계 실증
○ 국정원 '국가 망 보안체계(N2SF) 가이드라인 1.0' 기반의 데이터 중요도별 차등 보안 통제 체계 구축
○ 기존 획일적 망분리를 탈피하여 공공 업무에서 외부 상용 AI(ChatGPT, Gemini 등)를 안전하게 활용할 수 있는 환경 구현
○ 공공 문서(HWPX/HWP/PDF)의 C·S·O 등급 자동 분류를 통해 기밀 유출 방지 및 상용 AI 연계 실증
○ 국정원 '국가 망 보안체계(N2SF) 가이드라인 1.0' 기반의 데이터 중요도별 차등 보안 통제 체계 구축
○ 기존 획일적 망분리를 탈피하여 공공 업무에서 외부 상용 AI(ChatGPT, Gemini 등)를 안전하게 활용할 수 있는 환경 구현
○ 공공 문서(HWPX/HWP/PDF)의 C·S·O 등급 자동 분류를 통해 기밀 유출 방지 및 상용 AI 연계 실증
작 품 특 징
○ Streamlit 웹 UI를 이용한 직관적인 문서 업로드, C·S·O 등급 분류 및 외부 AI 연계 통제 현황 실시간 시각화
○ 외부 AI(ChatGPT, Gemini API) 연동 시 C(기밀) 원천 차단, S(민감) 비식별화 후 전송, O(공개) 자유 활용 차등 통제
○ 정규식 기반 개인정보(주민번호 등) 실시간 마스킹 처리 후 외부 AI 전송으로 안전한 프롬프트 보안 구현
○ 공공 표준 HWPX/PDF 다중 서식 자동 파싱 및 담당자 승인(Human-in-the-Loop) 감사 로그 생성
○ Streamlit 웹 UI를 이용한 직관적인 문서 업로드, C·S·O 등급 분류 및 외부 AI 연계 통제 현황 실시간 시각화
○ 외부 AI(ChatGPT, Gemini API) 연동 시 C(기밀) 원천 차단, S(민감) 비식별화 후 전송, O(공개) 자유 활용 차등 통제
○ 정규식 기반 개인정보(주민번호 등) 실시간 마스킹 처리 후 외부 AI 전송으로 안전한 프롬프트 보안 구현
○ 공공 표준 HWPX/PDF 다중 서식 자동 파싱 및 담당자 승인(Human-in-the-Loop) 감사 로그 생성
○ Streamlit 웹 UI를 이용한 직관적인 문서 업로드, C·S·O 등급 분류 및 외부 AI 연계 통제 현황 실시간 시각화
○ 외부 AI(ChatGPT, Gemini API) 연동 시 C(기밀) 원천 차단, S(민감) 비식별화 후 전송, O(공개) 자유 활용 차등 통제
○ 정규식 기반 개인정보(주민번호 등) 실시간 마스킹 처리 후 외부 AI 전송으로 안전한 프롬프트 보안 구현
○ 공공 표준 HWPX/PDF 다중 서식 자동 파싱 및 담당자 승인(Human-in-the-Loop) 감사 로그 생성
활용방안 및
기대효과
○ 외부 최신 초거대 AI(ChatGPT, Gemini)를 공공 행정에 안전하게 접목하여 문서 요약 및 분석 업무 효율 극대화
○ 중요 문서(C/S)의 외부 AI 유출을 원천 차단하여 N2SF 보안 가이드라인 준수 및 행정 신뢰성 확보
○ 공공기관의 차세대 N2SF 보안 체계 전환을 위한 실무 검증 모델로 활용 및 감사 추적성 확보
○ 외부 최신 초거대 AI(ChatGPT, Gemini)를 공공 행정에 안전하게 접목하여 문서 요약 및 분석 업무 효율 극대화
○ 중요 문서(C/S)의 외부 AI 유출을 원천 차단하여 N2SF 보안 가이드라인 준수 및 행정 신뢰성 확보
○ 공공기관의 차세대 N2SF 보안 체계 전환을 위한 실무 검증 모델로 활용 및 감사 추적성 확보
○ 외부 최신 초거대 AI(ChatGPT, Gemini)를 공공 행정에 안전하게 접목하여 문서 요약 및 분석 업무 효율 극대화
○ 중요 문서(C/S)의 외부 AI 유출을 원천 차단하여 N2SF 보안 가이드라인 준수 및 행정 신뢰성 확보
○ 공공기관의 차세대 N2SF 보안 체계 전환을 위한 실무 검증 모델로 활용 및 감사 추적성 확보"""

PROPOSAL_PPTX_TEXT = """[슬라이드 1]
2024-2 보안 캡스톤 프로젝트 제안
PASSBOX (N2SF with AI)
폐쇄망(Air-Gapped) 환경을 위한 On-Device 경량 LLM 기반
공공 문서 다층보안(C·S·O) 자동 분류 및 설명 가능 AI 보조 시스템
소속: 한국폴리텍대학 대전캠퍼스 클라우드보안과 (하이테크과정)
팀원: 윤상훈 (팀장 / UI·통합), 이하준 (파이프라인·파서), 이학민 (AI엔진·네트워크 검증)
핵심 가치: ① 완전 폐쇄망(외부 통신 Zero)  ② 정규식+경량LLM 하이브리드  ③ Human-in-the-Loop 실증
[슬라이드 2]
01. BACKGROUND & CHALLENGE
왜 지금 N2SF 자동 분류가 필요한가?
20여 년 만의 국가 망분리 정책 대전환(MLS)과 공공기관의 현실적 한계
🏛️ 국가 정책 대전환
• 국정원 N2SF(다층보안체계) 도입
• 획일적 물리적 망분리 해제
• 데이터를 C(기밀) / S(민감) / O(공개) 3단계로 차등 분류 의무화
• 등급에 따라 클라우드/SaaS 활용 및 차등 보안 통제 적용
📂 수백만 건 레거시 문서
• 수십 년간 축적된 HWP / PDF 문서가 기관당 수십만~수백만 건
• 사람이 일일이 열어보고 등급을 판정하는 것은 물리적 불가능
• 수동 검토 시 수억 원의 외주 비용 및 검토 인력의 기밀 열람 위험
🔒 폐쇄망 규제 & 책임 소재
• ChatGPT 등 클라우드 AI 사용 법적 불가 (국정원 망분리 위반)
• AI가 C(기밀)를 O(공개)로 오분류 시 담당 공무원의 법적/징계 책임
• 100% 자동화가 아닌 설명 가능한 보조 도구(Human-in-the-Loop) 필수
[슬라이드 3]
02. MARKET GAP ANALYSIS
기존 시장의 3대 한계와 PASSBOX의 차별화
극단적인 두 선택지(수억 원대 대형 랙 vs 무식한 키워드 스캐너) 사이의 혁신적 해법
비교 항목별 기존 솔루션 vs PASSBOX
1. 대기업 온프레미스 AI 랙 (삼성SDS, LG CNS 등)
- 한계: 수억 원대 GPU 인프라 서버 랙 구축 필수 ➔ 일반 지자체·산하기관 예산상 도입 불가능
- PASSBOX: 일반 업무용 PC/단일 서버에서도 구동되는 양자화 초경량 Local LLM(Ollama) 탑재 (도입 비용 1/100)
2. 전통 보안 업체 파일 스캐너 (소만사, 파수 등)
- 한계: 단순 정규식(주민번호, '기밀' 단어 검색) 중심 ➔ 문서 맥락(Context)을 이해하지 못해 오탐 수만 건 발생
- PASSBOX: 1차 정규식 초고속 필터링 + 2차 Local LLM 문맥 심층 분석의 '하이브리드 파이프라인'
3. 클라우드 AI 서비스 (OpenAI, 네이버 클로바 등)
- 한계: 인터넷망 외부 서버로 문서 데이터 전송 ➔ 공공 망분리 보안 규정 위반(데이터 유출 위협)
- PASSBOX: 100% 완전 격리 폐쇄망(Air-Gapped) On-Premise 구동 ➔ Wireshark 검증 외부 트래픽 0건
[슬라이드 4]
03. SYSTEM ARCHITECTURE
PASSBOX 핵심 처리 파이프라인
다중 문서 파싱부터 2단계 하이브리드 분류, 보안 검증까지의 완전 폐쇄망 구조
Step 1. 다중 문서 파서
• 공공 표준 HWPX 직접 파싱
• 레거시 HWP 텍스트 스트림 추출
• PDF (pypdf), DOCX, TXT 완벽 지원
• 무거운 외부 프로그램 의존성 배제
Step 2. 1차 정규식 필터
• 주민번호, 여권번호 패턴 탐지
• 전화번호, 금융계좌 탐지
• 고유식별정보 발견 즉시 S등급 후보군 선별
• 초고속 전처리로 LLM 부하 경감
Step 3. 2차 Local LLM
• Ollama 기반 경량 모델 구동
• 문서 전체 문맥 및 요약 분석
• C(기밀)/S(민감)/O(공개) 최종 판정
• '설명 가능한 판단 근거' 생성
Step 4. UI & Human 승인
• Streamlit 반응형 웹 대시보드
• AI 제안 등급 + 근거 키워드 표시
• 담당 공무원 1-Click 최종 승인
• 감사 로그 및 CSV 내보내기
[슬라이드 5]
04. KEY DIFFERENTIATORS
교수님과 심사위원을 사로잡을 3대 보안 특화 기능
보안학과 캡스톤 프로젝트만의 정체성을 드러내는 강력한 엣지 포인트
🛡️ 보수적 Fail-Safe 설계
• 문서 파싱 실패 / 파일 손상
• 암호화 파일 / OCR 판독 불가 시
• AI 판단 신뢰도 미달 시
👉 시스템이 스스로 가장 안전한 '최상위 보안 등급(C/S)'으로 보수적 격상 처리
보안의 기본 제1원칙(Fail-Secure)을 완벽하게 구현하여 데이터 유출 위험 0% 보장
📶 Wireshark 패킷 0건 입증
• 단순 '폐쇄망입니다'라는 말 대신
• Wireshark 실시간 패킷 캡처 시연
• 문서 업로드 및 AI 분석 전 과정에서
외부 DNS/HTTPS 트래픽 0건 입증
(127.0.0.1 내부 루프백 통신만 허용)
심사위원에게 가장 확실한 기술적 신뢰도와 시연 임팩트를 전달
⚖️ Human-in-the-Loop
• 100% 무인 자동화가 아닌
'보안 담당자 보조 도구'로 포지셔닝
• AI는 초안 추천 + 판단 근거 제시
• 담당 공무원이 최종 확인 버튼 클릭
• 수정 사유 및 감사 로그 자동 기록
공공기관 행정 감사의 책임 추적성(Audit Trail) 요건 완벽 충족
[슬라이드 6]
05. LIVE DEMO PLAN
7주차 중간 시연 및 11주차 최종 시연 시나리오
수업 운영안(PDF) 필수 평가 요건인 'Core Flow 실시간 시연' 완벽 대비
실시간 라이브 시연 4단계 시나리오 구성
[Scene 1] Wireshark 패킷 캡처 시작
- 외부 인터페이스 패킷 모니터링 활성화 (외부 송수신 0건 대기 상태 확인)
[Scene 2] 다중 유형 문서 일괄 드래그 앤 드롭 업로드
- O등급 샘플: 공공누리(KOGL) 공개 행정 보도자료 (HWPX)
- S등급 샘플: 가상 주민번호·전화번호가 포함된 복지 신청서 양식 (DOCX)
- C등급 샘플: 내부 클라우드 아키텍처 및 대외비 회의록 (PDF)
- 예외 샘플: 파손/암호화된 비정상 파일 (Fail-Safe 동작 검증용)
[Scene 3] 분석 결과 대시보드 확인
- 3초 내 실시간 분석 완료: C/S/O 등급 태그 + 주요 근거 키워드 하이라이트
- 파손된 파일은 Fail-Safe 로직에 의해 자동으로 C등급 격상 및 경고 알림 확인
[Scene 4] 담당자 승인 및 감사 로그 출력
- 담당자가 필요시 등급 수정 후 [최종 승인] 버튼 클릭 ➔ CSV 감사 보고서 즉시 다운로드
- Wireshark 화면 복귀: 전체 과정 중 외부 인터넷 패킷 0건(Zero Outbound) 실시간 입증 완료!
[슬라이드 7]
06. ROADMAP & MILESTONES
11주차 완성 로드맵 및 단계별 산출물
수업 운영안(PDF)의 Gantt Chart 기준에 맞춘 체계적 일정 관리
주차별 마일스톤 및 필수 산출물
• W01 ~ W02 (기획 & 설계) : 주제 확정, WBS / Gantt Chart 작성, 역할 분담 및 프로젝트 저장소 개설
• W03 ~ W04 (환경 & 데이터) : Ollama 로컬 LLM 환경 셋팅, C/S/O 테스트 문서 30건 데이터셋 구축
• W05 ~ W06 (최소 구현 MVP) : HWPX/PDF 텍스트 추출 모듈, 정규식 필터, Streamlit 기본 UI 연동
🚩 [W07 마일스톤: 중간 시연] 핵심 Core Flow(업로드 ➔ 분석 ➔ 결과 표시) 라이브 시연 및 예외 1건 검증
• W08 ~ W09 (확장 구현 & 고도화) : Fail-Safe 보수적 격상 로직, CSV 다운로드, Wireshark 패킷 검증
• W10 ~ W11 (통합 테스트 & 최종 발표) : 30건 전수 테스트, 오분류 분석표 작성, 최종 결과물 시연 및 발표
[슬라이드 8]
07. TEAM R&R
역할 분담 및 협업 체계
팀원 3인의 명확한 전문성 분담을 통한 리스크 최소화 및 일정 준수
윤상훈 (팀장)
UI/UX & 시스템 총괄
• Streamlit 반응형 웹 대시보드 개발
• 파일 업로드 및 분석 결과 테이블 UI
• 담당자 수정(Human-in-the-Loop) UI
• CSV 결과 리포트 생성 및 감사 로그 관리
• 전체 일정(WBS) 조율 및 문서화 총괄
이하준 (팀원)
문서 파서 & 정규식 필터
• HWPX(공공표준) 자체 파서 구현
• PDF, DOCX, TXT 텍스트 추출기 개발
• 1차 정규식 민감정보(주민/계좌) 필터
• 기밀 키워드 사전 구축
• 파싱 에러 방어 및 Fail-Safe 로직 개발
이학민 (팀원)
AI 엔진 & 보안 네트워크 검증
• Ollama 로컬 LLM 환경 셋팅 및 최적화
• C/S/O 분류 프롬프트 엔지니어링
• 테스트 문서 30건 데이터셋 구축
• Wireshark 패킷 캡처 및 외부 트래픽 검증
• 오분류 사례 분석 및 정확도 개선
[슬라이드 9]
08. EXPECTED IMPACT
PASSBOX의 사회적·기술적 파급 효과
공공 보안 행정의 혁신과 실용적 가치 창출
💼 공공기관 실무 관점 기대효과
1. 문서 분류 소요 시간 95% 단축
- 건당 3~5분 걸리던 수작업 검토를 3초 내외로 단축
2. 막대한 인프라 도입 예산 절감
- 수억 원대 GPU 전용 랙 대신 일반 업무용 PC에서 On-Premise 구동
3. 외주 인력에 의한 기밀 유출 차단
- 외부 용역 없이 자체 시스템에서 완전 폐쇄적으로 분류 완료
4. 행정 책임성 완벽 보장
- Human-in-the-Loop 구조로 담당 공무원의 최종 권한 및 이력 보존
🚀 기술적 확장 가능성 (Next Steps)
1. 국정원 공인 망연계(자료전송) 시스템 연동
- O등급(공개) 판정 시 인터넷망 반출 자동 승인 큐 전송
2. 엔터프라이즈 DRM / 워터마크 솔루션 연동
- C등급(기밀) 판정 시 자동 암호화 태그 및 비인가 열람 차단
3. 공공기관 특화 sLLM LoRA 경량 파인튜닝
- 국가 기록물 분류 체계 및 기관별 관용어 학습을 통한 정확도 극대화
4. 기관 대규모 NAS 폴더 야간 자동 배치 스케줄러 확장
[슬라이드 10]
PASSBOX (N2SF with AI)
망분리 폐쇄망을 지키는 가장 스마트한 AI 보안 보조 시스템
11주간 완성도 높은 최소 구현(MVP) 및 검증된 보안 시연으로 보답하겠습니다.
감사합니다. 경청해 주셔서 고맙습니다.
[Q & A]"""

NATIONAL_SECRET_TEXT = (
    "본 문서는 2급 비밀로 분류되며, 국가 안보와 직결된 작전 세부 계획과 "
    "인원 명단을 포함하고 있다. 외부 유출 시 국가안전보장에 중대한 위해를 "
    "초래할 수 있다."
)


def test_capstone_work_description_docx_is_public_not_sensitive():
    """v1에서 S로 오분류됐던 실제 공개 문서 (표지 저자명만으로 오판하던 바이라인 트랩 케이스)."""
    result = classify(WORK_DESCRIPTION_DOCX_TEXT)
    assert result["recommended_grade"] == "O", result["reason"]


def test_proposal_deck_pptx_is_public_not_sensitive():
    """v1에서 S로 오분류됐던 실제 공개 문서 (청크 꼬리 탈문맥 오분류 케이스)."""
    result = classify(PROPOSAL_PPTX_TEXT)
    assert result["recommended_grade"] == "O", result["reason"]


def test_genuine_national_security_secret_is_still_flagged():
    """회귀 방지: 진짜 기밀 내용까지 O로 풀리면 안 된다."""
    result = classify(NATIONAL_SECRET_TEXT)
    assert result["recommended_grade"] in ("S", "C"), result["reason"]


@pytest.mark.parametrize(
    "label,text",
    [
        (
            "기밀 아님 명시",
            "본 문서는 기밀이 아닌 공개 자료입니다. 누구나 자유롭게 열람하고 배포할 수 있습니다. "
            "2026년도 동아리 활동 보고서이며, 행사 사진과 참가자 명단(비공개 동의 없이는 이름 미기재), "
            "그리고 다음 학기 계획을 담고 있습니다.",
        ),
        (
            "정책 설명(제도 자체)",
            "국가정보원은 공공기관 문서를 기밀, 민감, 공개 세 등급으로 나누어 관리하도록 안내하고 있습니다. "
            "이 안내문은 등급 분류 제도 자체를 설명하는 일반 교육 자료로, 누구나 참고할 수 있는 공개 문서입니다. "
            "구체적인 기밀 문서의 실제 내용은 포함되어 있지 않습니다.",
        ),
        (
            "공지사항 속 한 단어",
            "다음 주 월요일 전 직원 워크숍이 진행됩니다. 장소는 대강당이며 간식이 제공됩니다. "
            "참고로 이번 워크숍 자료집에는 기밀 등급 문서는 포함되지 않으니 자유롭게 공유해 주세요. "
            "참석 여부는 금요일까지 회신 바랍니다.",
        ),
    ],
)
def test_word_confidential_alone_does_not_force_c_grade(label, text):
    """'기밀'이라는 단어가 들어있다는 이유만으로 C로 끌려가면 안 된다 (키워드 숏컷 회귀 방지)."""
    result = classify(text)
    assert result["recommended_grade"] == "O", f"[{label}] {result['reason']}"
