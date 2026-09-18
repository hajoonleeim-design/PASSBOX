import type { AIChatResponse, CreateChatRequestInput, PostInspectionResult } from '../types/aiChat'
import { apiClient } from './client'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

// 채팅 응답은 검사(POST inspection)를 통과했을 때만 화면에 본문을 보여 줍니다.
// Defense in depth: only a VERIFIED response is permitted past the API boundary.
// The production API must also withhold raw provider content until verification.
function safeForClient(response: AIChatResponse): AIChatResponse {
  // 검증 전 응답에서는 content를 제외한 정보만 반환해 원문 노출을 막습니다.
  if (response.postInspection?.status === 'VERIFIED') return response
  const { content: _content, ...safeResponse } = response
  return safeResponse
}

interface BackendPostInspectionResult {
  status: PostInspectionResult['status']
  inspected_at?: string | null
  detection_type?: string | null
  user_message: string
  incident_id?: string | null
}

interface BackendChatResponse {
  request_id: string
  model: string
  policy_version: string
  payload_status: AIChatResponse['payloadStatus']
  response_status: AIChatResponse['responseStatus']
  decision_status: AIChatResponse['decisionStatus']
  post_inspection?: BackendPostInspectionResult | null
  created_at: string
  updated_at: string
  error_message?: string | null
  content?: string | null
}

function mapPostInspection(value?: BackendPostInspectionResult | null): PostInspectionResult | undefined {
  if (!value) return undefined
  return {
    status: value.status,
    inspectedAt: value.inspected_at ?? undefined,
    detectionType: value.detection_type ?? undefined,
    userMessage: value.user_message,
    incidentId: value.incident_id ?? undefined,
  }
}

function mapResponse(data: BackendChatResponse): AIChatResponse {
  return {
    requestId: data.request_id,
    model: data.model,
    policyVersion: data.policy_version,
    payloadStatus: data.payload_status,
    responseStatus: data.response_status,
    decisionStatus: data.decision_status,
    postInspection: mapPostInspection(data.post_inspection),
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    errorMessage: data.error_message ?? undefined,
    content: data.content ?? undefined,
  }
}

const requestPath = (requestId: string) => `/chat/requests/${encodeURIComponent(requestId)}`

export async function createChatRequest(input: CreateChatRequestInput): Promise<AIChatResponse> {
  if (useMock) { const { mockCreateChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockCreateChatRequest(input)) }
  const { data } = await apiClient.post<BackendChatResponse>('/chat/requests', input)
  return safeForClient(mapResponse(data))
}

export async function getChatRequest(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockGetChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockGetChatRequest(requestId)) }
  const { data } = await apiClient.get<BackendChatResponse>(requestPath(requestId))
  return safeForClient(mapResponse(data))
}

export async function sendToAI(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockSendToAI } = await import('../mocks/aiChat'); return safeForClient(await mockSendToAI(requestId)) }
  const { data } = await apiClient.post<BackendChatResponse>(`${requestPath(requestId)}/send`)
  return safeForClient(mapResponse(data))
}

export async function getPostInspection(requestId: string): Promise<PostInspectionResult | undefined> {
  if (useMock) { const { mockGetPostInspection } = await import('../mocks/aiChat'); return mockGetPostInspection(requestId) }
  const { data } = await apiClient.get<BackendPostInspectionResult | null>(`${requestPath(requestId)}/post-inspection`)
  return mapPostInspection(data)
}

export async function retryChatRequest(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockRetryChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockRetryChatRequest(requestId)) }
  const { data } = await apiClient.post<BackendChatResponse>(`${requestPath(requestId)}/retry`)
  return safeForClient(mapResponse(data))
}
