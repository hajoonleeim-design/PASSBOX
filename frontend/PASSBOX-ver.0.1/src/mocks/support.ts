import type { CreateInquiryInput, Inquiry, SupportContent, SupportResponse } from '../types/support'

const inquiries = new Map<string, Inquiry>()

const content: SupportContent = {
  help: [
    { id: 'upload', title: '문서 업로드', description: '문서 업로드 화면에서 파일을 선택한 뒤 서버 검증 상태를 확인합니다.' },
    { id: 'analysis', title: '분석 상태', description: '분석 Job ID로 접수부터 완료까지의 진행 상태를 다시 조회할 수 있습니다.' },
    { id: 'result', title: 'C/S/O 및 승인', description: '판정 결과에서 등급과 근거를 확인하고, S등급은 권한자 승인 후 진행됩니다.' },
    { id: 'response', title: 'AI 답변 확인', description: 'Post-Inspector 검증이 완료된 답변만 화면에 표시됩니다.' },
    { id: 'audit', title: '감사·증적', description: 'Request ID를 기준으로 처리 이력과 메타데이터 중심의 증적을 조회합니다.' },
    { id: 'access', title: '권한 기능', description: '정책 관리와 운영 현황은 역할과 서버 권한에 따라 제공됩니다.' },
  ],
  fileFormats: ['HWP', 'HWPX', 'PDF', 'PPT', 'PPTX', 'XLS', 'XLSX'],
  privacy: [
    { category: '개인정보', example: '가상의 사용자 식별 정보', caution: '개인을 식별할 수 있는 정보는 문의에 입력하지 마세요.' },
    { category: '인증정보', example: '비밀번호 또는 인증 토큰', caution: '비밀번호, 인증코드, 접근 토큰은 절대 공유하지 마세요.' },
    { category: '금융정보', example: '가상의 결제 식별 정보', caution: '결제·계좌 관련 정보는 제외하고 현상만 설명하세요.' },
    { category: '계정정보', example: '내부 계정 식별자', caution: '계정 전체 정보 대신 문제 발생 시각과 Inquiry ID를 사용하세요.' },
    { category: '보안정보', example: '보안 설정값', caution: '보안 설정의 원문이나 비밀값은 입력하지 마세요.' },
    { category: '기밀정보', example: '비공개 업무 내용', caution: '업무 원문 대신 마스킹된 요약을 제공하세요.' },
    { category: '기타 민감정보', example: '공개가 제한된 자료', caution: '민감할 수 있는 자료는 문의에 첨부하거나 복사하지 마세요.' },
  ],
  faqs: [
    { id: 'file', question: '어떤 파일을 업로드할 수 있나요?', answer: 'HWP, HWPX, PDF, PPT, PPTX, XLS, XLSX 형식을 지원합니다. 실제 크기와 개수 제한은 서버 정책을 따릅니다.' },
    { id: 'time', question: '분석에는 얼마나 걸리나요?', answer: '문서 크기와 대기열 상태에 따라 달라집니다. 분석 화면에서 Job ID와 진행 단계를 확인하세요.' },
    { id: 'grade', question: 'C/S/O는 무엇인가요?', answer: 'C는 전송 차단, S는 사람의 승인 필요, O는 정책 검증 완료 상태를 뜻합니다.' },
    { id: 'approval', question: 'S등급은 왜 승인이 필요한가요?', answer: '정책상 검토가 필요한 요청이므로 APPROVER 또는 ADMIN 역할의 승인이 필요합니다.' },
    { id: 'blocked', question: '분석 결과가 차단되면 어떻게 하나요?', answer: '차단 사유와 탐지 근거를 확인하고 민감정보를 제거하거나 마스킹한 뒤 새 요청을 만드세요.' },
    { id: 'answer', question: 'AI 답변은 언제 표시되나요?', answer: 'Post-Inspector 검증이 VERIFIED 상태가 된 뒤에만 표시됩니다.' },
    { id: 'audit', question: 'Audit/Evidence는 무엇인가요?', answer: 'Request ID를 기준으로 처리 단계, 승인 이력, 정책 및 증적 메타데이터를 확인하는 기능입니다.' },
    { id: 'inquiry', question: '문의 시 어떤 정보를 포함해야 하나요?', answer: '문제 발생 시각, Job ID 또는 Request ID, 오류 상태를 포함하세요. 비밀번호·토큰·원문 문서는 포함하지 마세요.' },
  ],
}

export async function mockGetSupportContent(scenario: string): Promise<SupportContent> {
  if (scenario === 'mock-network-error') throw new Error('NETWORK_ERROR')
  if (scenario === 'mock-forbidden') throw new Error('FORBIDDEN')
  if (scenario === 'mock-empty') return { help: [], faqs: [], privacy: [], fileFormats: [] }
  if (scenario !== 'mock-success') throw new Error('NOT_FOUND')
  return structuredClone(content)
}

export async function mockCreateInquiry(input: CreateInquiryInput, scenario: string): Promise<SupportResponse> {
  if (scenario === 'mock-network-error') throw new Error('NETWORK_ERROR')
  if (scenario === 'mock-forbidden') throw new Error('FORBIDDEN')
  const receivedAt = new Date().toISOString()
  const inquiryId = `INQ-${receivedAt.slice(0, 10).replaceAll('-', '')}-${String(inquiries.size + 1).padStart(4, '0')}`
  inquiries.set(inquiryId, { inquiryId, category: input.category, subject: input.subject.trim(), status: 'RECEIVED', createdAt: receivedAt, updatedAt: receivedAt, maskedContent: '[문의 원문은 표시하거나 브라우저에 보관하지 않습니다.]' })
  return { inquiryId, status: 'RECEIVED', receivedAt, message: '문의가 접수되었습니다. Inquiry ID를 통해 접수 상태를 확인할 수 있습니다.' }
}

export async function mockGetInquiry(inquiryId: string): Promise<Inquiry> {
  const inquiry = inquiries.get(inquiryId)
  if (!inquiry) throw new Error('NOT_FOUND')
  return structuredClone(inquiry)
}
// 지원 페이지를 개발할 때 쓰는 FAQ, 안내, 문의 응답 예시 데이터입니다.
