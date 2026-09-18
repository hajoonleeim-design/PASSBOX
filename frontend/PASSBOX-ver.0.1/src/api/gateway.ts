import { apiClient } from './client'

export interface GatewayForwardInput {
  provider: string
  model: string
  prompt?: string
}

export interface GatewayForwardResult {
  transmissionId: number
  approvalId: number | null
  documentId: number
  provider: string
  model: string
  gatewayMode: string
  policyVersion: string
  confirmedGrade: string
  policyDecision: string
  status: string
  postInspectionStatus: string | null
  response: string | null
  responseHash: string | null
  responseCategories: string[]
  createdAt: string
}

interface BackendGatewayForwardResponse {
  transmission_id: number
  approval_id?: number | null
  document_id: number
  provider: string
  model: string
  gateway_mode: string
  policy_version: string
  confirmed_grade: string
  policy_decision: string
  status: string
  post_inspection_status: string | null
  response: string | null
  response_hash: string | null
  response_categories: string[]
  created_at: string
}

function mapGatewayResponse(data: BackendGatewayForwardResponse): GatewayForwardResult {
  return {
    transmissionId: data.transmission_id,
    approvalId: data.approval_id ?? null,
    documentId: data.document_id,
    provider: data.provider,
    model: data.model,
    gatewayMode: data.gateway_mode,
    policyVersion: data.policy_version,
    confirmedGrade: data.confirmed_grade,
    policyDecision: data.policy_decision,
    status: data.status,
    postInspectionStatus: data.post_inspection_status,
    response: data.response,
    responseHash: data.response_hash,
    responseCategories: data.response_categories,
    createdAt: data.created_at,
  }
}

export async function forwardToGateway(
  documentId: number,
  input: GatewayForwardInput,
): Promise<GatewayForwardResult> {
  const { data } = await apiClient.post<BackendGatewayForwardResponse>(
    `/documents/${documentId}/gateway/forward`,
    {
      provider: input.provider,
      model: input.model,
      prompt: input.prompt?.trim() || null,
    },
  )
  return mapGatewayResponse(data)
}
