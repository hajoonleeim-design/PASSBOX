import type { AIChatResponse, CreateChatRequestInput } from '../types/aiChat'

const requests = new Map<string, AIChatResponse>()
const positions = new Map<string, number>()
const now = () => new Date().toISOString()

const copy = (request: AIChatResponse): AIChatResponse => ({
  ...request,
  postInspection: request.postInspection ? { ...request.postInspection } : undefined,
})

const base = (requestId: string): AIChatResponse => ({
  requestId,
  model: 'Mock Secure AI',
  policyVersion: 'POLICY-1.3',
  payloadStatus: 'PENDING',
  responseStatus: 'NOT_RECEIVED',
  decisionStatus: 'ALLOWED',
  createdAt: now(),
  updatedAt: now(),
})

const verified = (requestId: string): AIChatResponse => ({
  ...base(requestId),
  payloadStatus: 'VERIFIED',
  responseStatus: 'VERIFIED',
  postInspection: { status: 'VERIFIED', inspectedAt: now(), userMessage: 'AI 응답 보안 검증이 완료되었습니다.' },
  content: '검증을 통과한 Mock AI 응답입니다.',
})

const blocked = (requestId: string, failed = false): AIChatResponse => ({
  ...base(requestId),
  payloadStatus: 'VERIFIED',
  responseStatus: failed ? 'FAILED' : 'BLOCKED',
  postInspection: {
    status: failed ? 'FAILED' : 'BLOCKED',
    inspectedAt: now(),
    detectionType: '응답 보안 정책',
    userMessage: failed ? 'AI 응답 검증에 실패했습니다. 안전을 위해 원문을 표시하지 않습니다.' : 'AI 응답이 보안 정책에 의해 차단되었습니다.',
    incidentId: failed ? 'INC-MOCK-FAILED' : 'INC-MOCK-BLOCKED',
  },
})

function preset(requestId: string): AIChatResponse | null {
  if (['mock-success', 'mock-s-approved', 'mock-o'].includes(requestId)) return verified(requestId)
  if (requestId === 'mock-inspecting') return {
    ...base(requestId), payloadStatus: 'VERIFIED', responseStatus: 'POST_INSPECTING',
    postInspection: { status: 'INSPECTING', userMessage: 'AI 응답을 보안 검증하고 있습니다.' },
  }
  if (requestId === 'mock-blocked') return blocked(requestId)
  if (requestId === 'mock-failed') return blocked(requestId, true)
  if (requestId === 'mock-c') return { ...base(requestId), payloadStatus: 'BLOCKED', decisionStatus: 'BLOCKED', postInspection: { status: 'PENDING', userMessage: 'C등급 요청은 외부 AI 전송이 차단됩니다.' } }
  if (requestId === 'mock-s') return { ...base(requestId), payloadStatus: 'BLOCKED', decisionStatus: 'WAITING_APPROVAL', postInspection: { status: 'PENDING', userMessage: 'S등급 요청은 승인 전 전송할 수 없습니다.' } }
  if (requestId === 'mock-s-rejected') return { ...base(requestId), payloadStatus: 'BLOCKED', decisionStatus: 'REJECTED', postInspection: { status: 'PENDING', userMessage: '반려된 S등급 요청은 전송할 수 없습니다.' } }
  return null
}

export async function mockCreateChatRequest(input: CreateChatRequestInput): Promise<AIChatResponse> {
  if (!input.prompt.trim()) throw new Error('INVALID_PROMPT')
  const requestId = `MOCK-CHAT-${crypto.randomUUID().slice(0, 8).toUpperCase()}`
  const request = base(requestId)
  requests.set(requestId, request)
  positions.set(requestId, 0)
  return copy(request)
}

export async function mockGetChatRequest(requestId: string): Promise<AIChatResponse> {
  if (requestId === 'mock-network-error') throw new Error('NETWORK_ERROR')
  let request = requests.get(requestId)
  if (!request) {
    request = preset(requestId) ?? undefined
    if (!request) throw new Error('NOT_FOUND')
    requests.set(requestId, request)
  }
  const position = positions.get(requestId) ?? 99
  if (position < 4) {
    const stages: AIChatResponse[] = [
      { ...request, payloadStatus: 'VALIDATING', updatedAt: now() },
      { ...request, payloadStatus: 'VERIFIED', responseStatus: 'RECEIVED', updatedAt: now() },
      { ...request, payloadStatus: 'VERIFIED', responseStatus: 'POST_INSPECTING', postInspection: { status: 'INSPECTING', userMessage: 'AI 응답을 보안 검증하고 있습니다.' }, updatedAt: now() },
      { ...verified(requestId), updatedAt: now() },
    ]
    request = stages[position]
    requests.set(requestId, request)
    positions.set(requestId, position + 1)
  }
  return copy(request)
}

export async function mockSendToAI(requestId: string): Promise<AIChatResponse> {
  return mockGetChatRequest(requestId)
}

export async function mockGetPostInspection(requestId: string) {
  return (await mockGetChatRequest(requestId)).postInspection
}

export async function mockRetryChatRequest(requestId: string): Promise<AIChatResponse> {
  const current = await mockGetChatRequest(requestId)
  const next = base(requestId)
  requests.set(requestId, next)
  positions.set(requestId, 0)
  return copy({ ...next, model: current.model, policyVersion: current.policyVersion })
}
// AI 제공자를 호출하지 않고 채팅 및 사후 검사 흐름을 시험하기 위한 가짜 데이터입니다.
