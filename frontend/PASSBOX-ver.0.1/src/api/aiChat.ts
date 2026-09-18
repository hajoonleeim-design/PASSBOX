import type { AIChatResponse, CreateChatRequestInput, PostInspectionResult } from '../types/aiChat'

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

export async function createChatRequest(input: CreateChatRequestInput): Promise<AIChatResponse> {
  if (useMock) { const { mockCreateChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockCreateChatRequest(input)) }
  throw new Error('AI_CHAT_API_UNAVAILABLE')
}

export async function getChatRequest(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockGetChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockGetChatRequest(requestId)) }
  throw new Error('AI_CHAT_API_UNAVAILABLE')
}

export async function sendToAI(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockSendToAI } = await import('../mocks/aiChat'); return safeForClient(await mockSendToAI(requestId)) }
  throw new Error('AI_CHAT_API_UNAVAILABLE')
}

export async function getPostInspection(requestId: string): Promise<PostInspectionResult | undefined> {
  if (useMock) { const { mockGetPostInspection } = await import('../mocks/aiChat'); return mockGetPostInspection(requestId) }
  throw new Error('AI_CHAT_API_UNAVAILABLE')
}

export async function retryChatRequest(requestId: string): Promise<AIChatResponse> {
  if (useMock) { const { mockRetryChatRequest } = await import('../mocks/aiChat'); return safeForClient(await mockRetryChatRequest(requestId)) }
  throw new Error('AI_CHAT_API_UNAVAILABLE')
}
