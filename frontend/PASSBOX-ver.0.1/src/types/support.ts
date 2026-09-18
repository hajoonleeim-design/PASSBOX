export type SupportCategory = 'HELP' | 'FILE_FORMAT' | 'PRIVACY' | 'FAQ' | 'INQUIRY' | 'ERROR' | 'CONTACT'
export type InquiryStatus = 'RECEIVED' | 'IN_REVIEW' | 'ANSWERED' | 'CLOSED' | 'FAILED'

export interface Inquiry {
  inquiryId: string
  category: SupportCategory
  subject: string
  status: InquiryStatus
  createdAt: string
  updatedAt: string
  maskedContent: string
}

export interface SupportResponse {
  inquiryId: string
  status: InquiryStatus
  receivedAt: string
  message: string
}

export interface SupportArticle {
  id: string
  title: string
  description: string
}

export interface SupportFaq {
  id: string
  question: string
  answer: string
}

export interface PrivacyGuide {
  category: string
  example: string
  caution: string
}

export interface SupportContent {
  help: SupportArticle[]
  faqs: SupportFaq[]
  privacy: PrivacyGuide[]
  fileFormats: string[]
}

export interface CreateInquiryInput {
  category: SupportCategory
  subject: string
  content: string
}
// 지원 센터의 FAQ, 연락처, 문의 등록에 사용하는 데이터 모양입니다.
