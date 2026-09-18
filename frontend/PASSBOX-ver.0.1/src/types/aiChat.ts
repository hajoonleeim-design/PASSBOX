import type { DecisionStatus } from './decision'

export type PayloadStatus = 'PENDING' | 'VALIDATING' | 'VERIFIED' | 'BLOCKED' | 'FAILED'
export type AIResponseStatus = 'NOT_RECEIVED' | 'RECEIVED' | 'POST_INSPECTING' | 'VERIFIED' | 'BLOCKED' | 'FAILED' | 'UNKNOWN'
export type PostInspectionStatus = 'PENDING' | 'INSPECTING' | 'VERIFIED' | 'BLOCKED' | 'FAILED' | 'UNKNOWN'
export interface PostInspectionResult { status: PostInspectionStatus; inspectedAt?: string; detectionType?: string; userMessage: string; incidentId?: string }
export interface AIChatRequest {
  requestId: string
  model: string
  policyVersion: string
  payloadStatus: PayloadStatus
  responseStatus: AIResponseStatus
  decisionStatus: DecisionStatus
  postInspection?: PostInspectionResult
  createdAt: string
  updatedAt: string
  errorMessage?: string
}
export interface AIChatResponse extends AIChatRequest { content?: string }
export interface CreateChatRequestInput { prompt: string }
// AI 채팅 요청, 응답, 사후 검사 결과의 데이터 모양을 정의합니다.
