import type { ClassificationDecision, DecisionActor, RejectDecisionInput } from '../types/decision'
import { apiClient } from './client'
import { approveDecision as approveMockDecision, getDecision as getMockDecision, rejectDecision as rejectMockDecision } from './decisions'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

interface BackendApprovalHistoryEntry {
  id: string
  action: string
  actor: { user_id: string; display_name: string; role: string }
  acted_at: string
  reason: string | null
}

interface BackendDecisionResponse {
  request_id: number
  job_id: number | null
  file_name: string
  grade: 'C' | 'S' | 'O'
  grade_name: string
  description: string
  detections: ClassificationDecision['detections']
  policy_version: string
  masking_preview: string | null
  block_reason: string | null
  status: ClassificationDecision['status']
  created_at: string
  decided_at: string
  approval_id: number | null
  history: BackendApprovalHistoryEntry[]
}

const toRequestNumber = (requestId: string) => {
  const value = Number(requestId)
  if (!Number.isInteger(value) || value < 1) throw new Error('NOT_FOUND')
  return value
}

function mapDecision(data: BackendDecisionResponse): ClassificationDecision {
  return {
    requestId: String(data.request_id),
    jobId: data.job_id === null ? undefined : String(data.job_id),
    fileName: data.file_name,
    grade: data.grade,
    gradeName: data.grade_name,
    description: data.description,
    detections: data.detections,
    policyVersion: data.policy_version,
    maskingPreview: data.masking_preview ?? undefined,
    blockReason: data.block_reason ?? undefined,
    status: data.status,
    createdAt: data.created_at,
    decidedAt: data.decided_at,
    approvalId: data.approval_id ?? undefined,
    history: data.history.map((item) => ({
      id: item.id,
      action: item.action === 'APPROVED' ? 'APPROVED' : 'REJECTED',
      actor: {
        userId: item.actor.user_id,
        displayName: item.actor.display_name,
        role: item.actor.role as DecisionActor['role'],
      },
      actedAt: item.acted_at,
      reason: item.reason ?? undefined,
    })),
  }
}

export async function getDecisionSource(requestId: string): Promise<ClassificationDecision> {
  if (useMock) return getMockDecision(requestId)
  const { data } = await apiClient.get<BackendDecisionResponse>(
    `/requests/${toRequestNumber(requestId)}/decision`,
  )
  return mapDecision(data)
}

export async function approveDecisionSource(requestId: string, actor: DecisionActor): Promise<ClassificationDecision> {
  if (useMock) return approveMockDecision(requestId, actor)
  const current = await getDecisionSource(requestId)
  if (!current.approvalId) throw new Error('INVALID_TRANSITION')
  await apiClient.post(`/approvals/${current.approvalId}/approve`, { comment: null })
  return getDecisionSource(requestId)
}

export async function rejectDecisionSource(requestId: string, input: RejectDecisionInput): Promise<ClassificationDecision> {
  if (useMock) return rejectMockDecision(requestId, input)
  if (!input.reason.trim()) throw new Error('INVALID_REASON')
  const current = await getDecisionSource(requestId)
  if (!current.approvalId) throw new Error('INVALID_TRANSITION')
  await apiClient.post(`/approvals/${current.approvalId}/reject`, { comment: input.reason.trim() })
  return getDecisionSource(requestId)
}
