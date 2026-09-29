import { apiClient } from './client'
import type { CreateReviewRequestInput, DecideReviewRequestInput, ReviewRequestItem } from '../types/reviewRequest'
import type { SecurityGrade } from '../types/security'

interface BackendReviewRequestResponse {
  review_request_id: number
  document_id: number
  file_name: string
  original_grade: SecurityGrade
  reason: string
  flag_for_retraining: boolean
  status: ReviewRequestItem['status']
  requested_by: number
  requested_by_name: string
  resolved_by: number | null
  resolution_comment: string | null
  resolved_grade: SecurityGrade | null
  created_at: string
  resolved_at: string | null
}

function mapReviewRequest(data: BackendReviewRequestResponse): ReviewRequestItem {
  return {
    reviewRequestId: data.review_request_id,
    documentId: data.document_id,
    fileName: data.file_name,
    originalGrade: data.original_grade,
    reason: data.reason,
    flagForRetraining: data.flag_for_retraining,
    status: data.status,
    requestedBy: data.requested_by,
    requestedByName: data.requested_by_name,
    resolvedBy: data.resolved_by ?? undefined,
    resolutionComment: data.resolution_comment ?? undefined,
    resolvedGrade: data.resolved_grade ?? undefined,
    createdAt: data.created_at,
    resolvedAt: data.resolved_at ?? undefined,
  }
}

export async function createReviewRequest(documentId: number, input: CreateReviewRequestInput): Promise<ReviewRequestItem> {
  const { data } = await apiClient.post<BackendReviewRequestResponse>(
    `/review-requests/documents/${documentId}`,
    { reason: input.reason, flag_for_retraining: input.flagForRetraining },
  )
  return mapReviewRequest(data)
}

export async function getPendingReviewRequests(): Promise<ReviewRequestItem[]> {
  const { data } = await apiClient.get<BackendReviewRequestResponse[]>('/review-requests')
  return data.map(mapReviewRequest)
}

export async function decideReviewRequest(reviewRequestId: number, input: DecideReviewRequestInput): Promise<ReviewRequestItem> {
  const { data } = await apiClient.post<BackendReviewRequestResponse>(
    `/review-requests/${reviewRequestId}/decide`,
    { action: input.action, comment: input.comment?.trim() || null, new_grade: input.newGrade ?? null },
  )
  return mapReviewRequest(data)
}
