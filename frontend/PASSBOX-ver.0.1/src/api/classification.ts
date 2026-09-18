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
