import { apiClient } from './client'

export interface ClassificationRecommendation {
  recommendationId: number
  documentId: number
  recommendedGrade: string | null
  confidence: number | null
  reason: string
  modelVersion: string
  status: string
  createdAt: string
}

interface BackendClassificationRecommendation {
  recommendation_id: number
  document_id: number
  recommended_grade: string | null
  confidence: number | null
  reason: string
  model_version: string
  status: string
  created_at: string
}

export interface ClassificationDecision {
  decisionId: number
  documentId: number
  recommendationId: number | null
  recommendedGrade: string | null
  confirmedGrade: string
  comment: string | null
  confirmedBy: number
  createdAt: string
}

interface BackendClassificationDecision {
  decision_id: number
  document_id: number
  recommendation_id: number | null
  recommended_grade: string | null
  confirmed_grade: string
  comment: string | null
  confirmed_by: number
  created_at: string
}

function mapRecommendation(data: BackendClassificationRecommendation): ClassificationRecommendation {
  return {
    recommendationId: data.recommendation_id,
    documentId: data.document_id,
    recommendedGrade: data.recommended_grade,
    confidence: data.confidence,
    reason: data.reason,
    modelVersion: data.model_version,
    status: data.status,
    createdAt: data.created_at,
  }
}

export async function recommendClassification(
  documentId: number,
): Promise<ClassificationRecommendation> {
  const { data } = await apiClient.post<BackendClassificationRecommendation>(
    `/documents/${documentId}/classification/recommend`,
  )
  return mapRecommendation(data)
}

export async function getClassificationRecommendation(
  documentId: number,
): Promise<ClassificationRecommendation> {
  const { data } = await apiClient.get<BackendClassificationRecommendation>(
    `/documents/${documentId}/classification/recommendation`,
  )
  return mapRecommendation(data)
}

export async function getClassificationDecision(
  documentId: number,
): Promise<ClassificationDecision> {
  const { data } = await apiClient.get<BackendClassificationDecision>(
    `/documents/${documentId}/classification/decision`,
  )
  return {
    decisionId: data.decision_id,
    documentId: data.document_id,
    recommendationId: data.recommendation_id,
    recommendedGrade: data.recommended_grade,
    confirmedGrade: data.confirmed_grade,
    comment: data.comment,
    confirmedBy: data.confirmed_by,
    createdAt: data.created_at,
  }
}

export async function confirmClassification(
  documentId: number,
  confirmedGrade: 'C' | 'S' | 'O',
  comment?: string,
): Promise<ClassificationDecision> {
  const { data } = await apiClient.post<BackendClassificationDecision>(
    `/documents/${documentId}/classification/confirm`,
    { confirmed_grade: confirmedGrade, comment: comment?.trim() || null },
  )
  return {
    decisionId: data.decision_id,
    documentId: data.document_id,
    recommendationId: data.recommendation_id,
    recommendedGrade: data.recommended_grade,
    confirmedGrade: data.confirmed_grade,
    comment: data.comment,
    confirmedBy: data.confirmed_by,
    createdAt: data.created_at,
  }
}

export async function downloadSourceDocument(documentId: number): Promise<void> {
  const { data, headers } = await apiClient.get<Blob>(`/documents/${documentId}/source-document`, {
    responseType: 'blob',
  })
  const disposition = headers['content-disposition'] as string | undefined
  const encodedName = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  const quotedName = disposition?.match(/filename="?([^";]+)"?/i)?.[1]
  const fileName = encodedName ? decodeURIComponent(encodedName) : (quotedName ?? `document-${documentId}`)
  const objectUrl = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = fileName
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

export interface PendingConfirmation {
  documentId: number
  fileName: string
  createdAt: string
  recommendedGrade: string | null
  confidence: number | null
  modelVersion: string | null
  uploadedByMe: boolean
}

interface BackendPendingConfirmation {
  document_id: number
  file_name: string
  created_at: string
  recommended_grade: string | null
  confidence: number | null
  model_version: string | null
  uploaded_by_me: boolean
}

export async function getPendingConfirmations(): Promise<PendingConfirmation[]> {
  const { data } = await apiClient.get<BackendPendingConfirmation[]>('/documents/classification/pending')
  return data.map((item) => ({
    documentId: item.document_id,
    fileName: item.file_name,
    createdAt: item.created_at,
    recommendedGrade: item.recommended_grade,
    confidence: item.confidence,
    modelVersion: item.model_version,
    uploadedByMe: item.uploaded_by_me,
  }))
}

export interface BulkConfirmResult {
  confirmed: number
  skipped: number
  items: { documentId: number; result: 'CONFIRMED' | 'SKIPPED'; confirmedGrade: string | null; reason: string | null }[]
}

interface BackendBulkConfirmResult {
  confirmed: number
  skipped: number
  items: { document_id: number; result: 'CONFIRMED' | 'SKIPPED'; confirmed_grade: string | null; reason: string | null }[]
}

// 선택한 문서를 AI 추천 등급 그대로 한 번에 확정한다(추천과 다른 등급으로는 확정할 수 없다).
export async function bulkConfirmRecommended(documentIds: number[], comment?: string): Promise<BulkConfirmResult> {
  const { data } = await apiClient.post<BackendBulkConfirmResult>('/documents/classification/bulk-confirm', {
    document_ids: documentIds,
    comment: comment?.trim() || null,
  })
  return {
    confirmed: data.confirmed,
    skipped: data.skipped,
    items: data.items.map((item) => ({
      documentId: item.document_id,
      result: item.result,
      confirmedGrade: item.confirmed_grade,
      reason: item.reason,
    })),
  }
}
