import type { CreateInquiryInput, Inquiry, SupportContent, SupportResponse } from '../types/support'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

export async function getSupportContent(scenario: string): Promise<SupportContent> {
  if (useMock) { const { mockGetSupportContent } = await import('../mocks/support'); return mockGetSupportContent(scenario) }
  throw new Error('SUPPORT_API_UNAVAILABLE')
}

export async function createInquiry(input: CreateInquiryInput, scenario: string): Promise<SupportResponse> {
  if (useMock) { const { mockCreateInquiry } = await import('../mocks/support'); return mockCreateInquiry(input, scenario) }
  throw new Error('SUPPORT_API_UNAVAILABLE')
}

export async function getInquiry(inquiryId: string): Promise<Inquiry> {
  if (useMock) { const { mockGetInquiry } = await import('../mocks/support'); return mockGetInquiry(inquiryId) }
  throw new Error('SUPPORT_API_UNAVAILABLE')
}
// 고객 지원 콘텐츠와 문의 등록 요청을 담당하는 API 계층입니다.
