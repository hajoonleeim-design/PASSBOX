import { apiClient } from './client'

export interface ApprovalItem {
  approvalId: number
  documentId: number
  transmissionId: number
  provider: string
  model: string
  gatewayMode: string
  maskingVersion: string
  maskingCategories: string[]
  status: string
  transmissionStatus: string
  policyDecision: string
  postInspectionStatus: string | null
  response: string | null
  requestedBy: number
  decidedBy: number | null
  decisionComment: string | null
  createdAt: string
  decidedAt: string | null
}

interface BackendApprovalResponse {
  approval_id: number
  document_id: number
  transmission_id: number
  provider: string
  model: string
  gateway_mode: string
  masking_version: string
  masking_categories: string[]
  status: string
  transmission_status: string
  policy_decision: string
  post_inspection_status: string | null
  response: string | null
  requested_by: number
  decided_by: number | null
  decision_comment: string | null
  created_at: string
  decided_at: string | null
}

function mapApproval(data: BackendApprovalResponse): ApprovalItem {
  return {
    approvalId: data.approval_id,
    documentId: data.document_id,
    transmissionId: data.transmission_id,
    provider: data.provider,
    model: data.model,
    gatewayMode: data.gateway_mode,
    maskingVersion: data.masking_version,
    maskingCategories: data.masking_categories,
    status: data.status,
    transmissionStatus: data.transmission_status,
    policyDecision: data.policy_decision,
    postInspectionStatus: data.post_inspection_status,
    response: data.response,
    requestedBy: data.requested_by,
    decidedBy: data.decided_by,
    decisionComment: data.decision_comment,
    createdAt: data.created_at,
    decidedAt: data.decided_at,
  }
}

export async function getPendingApprovals(): Promise<ApprovalItem[]> {
  const { data } = await apiClient.get<BackendApprovalResponse[]>('/approvals/pending')
  return data.map(mapApproval)
}

export async function getRetryableApprovals(): Promise<ApprovalItem[]> {
  const { data } = await apiClient.get<BackendApprovalResponse[]>('/approvals/retryable')
  return data.map(mapApproval)
}

export async function retryApproval(approvalId: number): Promise<ApprovalItem> {
  const { data } = await apiClient.post<BackendApprovalResponse>(`/approvals/${approvalId}/retry`)
  return mapApproval(data)
}

export async function decideApproval(
  approvalId: number,
  action: 'approve' | 'reject',
  comment?: string,
): Promise<ApprovalItem> {
  const { data } = await apiClient.post<BackendApprovalResponse>(
    `/approvals/${approvalId}/${action}`,
    { comment: comment?.trim() || null },
  )
  return mapApproval(data)
}
