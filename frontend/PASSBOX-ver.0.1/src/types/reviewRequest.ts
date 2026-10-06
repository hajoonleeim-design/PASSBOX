import type { SecurityGrade } from './security'

export type ReviewRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface ReviewRequestItem {
  reviewRequestId: number
  documentId: number
  fileName: string
  originalGrade: SecurityGrade
  reason: string
  flagForRetraining: boolean
  status: ReviewRequestStatus
  requestedBy: number
  requestedByName: string
  resolvedBy?: number
  resolutionComment?: string
  resolvedGrade?: SecurityGrade
  createdAt: string
  resolvedAt?: string
  hoursPending: number
  isEscalated: boolean
}

export interface CreateReviewRequestInput { reason: string; flagForRetraining: boolean }
export interface DecideReviewRequestInput { action: 'approve' | 'reject'; comment?: string; newGrade?: SecurityGrade }
// C등급(전송 차단) 판정에 대한 재검토 요청 데이터 모양을 정의합니다.
