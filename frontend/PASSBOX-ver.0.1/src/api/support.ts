import type { CreateInquiryInput, Inquiry, SupportContent, SupportResponse } from '../types/support'
import { apiClient } from './client'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

export async function getSupportContent(scenario: string): Promise<SupportContent> {
  if (useMock) { const { mockGetSupportContent } = await import('../mocks/support'); return mockGetSupportContent(scenario) }
  const { data } = await apiClient.get<BackendSupportContent>('/support/content')
  return mapContent(data)
}

export async function createInquiry(input: CreateInquiryInput, scenario: string): Promise<SupportResponse> {
  if (useMock) { const { mockCreateInquiry } = await import('../mocks/support'); return mockCreateInquiry(input, scenario) }
  const { data } = await apiClient.post<BackendSupportResponse>('/support/inquiries', input)
  return {
    inquiryId: data.inquiry_id,
    status: data.status,
    receivedAt: data.received_at,
    message: data.message,
  }
}

export async function getInquiry(inquiryId: string): Promise<Inquiry> {
  if (useMock) { const { mockGetInquiry } = await import('../mocks/support'); return mockGetInquiry(inquiryId) }
  const { data } = await apiClient.get<BackendInquiry>(`/support/inquiries/${encodeURIComponent(inquiryId)}`)
  return {
    inquiryId: data.inquiry_id,
    category: data.category,
    subject: data.subject,
    status: data.status,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    maskedContent: data.masked_content,
  }
}

interface BackendSupportContent {
  help: SupportContent['help']
  faqs: SupportContent['faqs']
  privacy: SupportContent['privacy']
  file_formats: string[]
}

interface BackendSupportResponse {
  inquiry_id: string
  status: SupportResponse['status']
  received_at: string
  message: string
}

interface BackendInquiry {
  inquiry_id: string
  category: Inquiry['category']
  subject: string
  status: Inquiry['status']
  created_at: string
  updated_at: string
  masked_content: string
}

function mapContent(data: BackendSupportContent): SupportContent {
  return { help: data.help, faqs: data.faqs, privacy: data.privacy, fileFormats: data.file_formats }
}
// 고객 지원 콘텐츠와 문의 등록 요청을 담당하는 API 계층입니다.
