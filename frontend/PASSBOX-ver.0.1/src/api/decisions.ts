import type { ClassificationDecision, DecisionActor, RejectDecisionInput } from '../types/decision'
const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL
export async function getDecision(requestId: string): Promise<ClassificationDecision> { if (useMock) { const { mockGetDecision } = await import('../mocks/decisions'); return mockGetDecision(requestId) } throw new Error('승인된 판정 결과 API 명세가 아직 연결되지 않았습니다.') }
export async function approveDecision(requestId: string, actor: DecisionActor): Promise<ClassificationDecision> { if (useMock) { const { mockApproveDecision } = await import('../mocks/decisions'); return mockApproveDecision(requestId, actor) } throw new Error('승인된 승인 API 명세가 아직 연결되지 않았습니다.') }
export async function rejectDecision(requestId: string, input: RejectDecisionInput): Promise<ClassificationDecision> { if (useMock) { const { mockRejectDecision } = await import('../mocks/decisions'); return mockRejectDecision(requestId, input) } throw new Error('승인된 반려 API 명세가 아직 연결되지 않았습니다.') }
// 보안 판정 결과의 조회·승인·반려 요청을 담당하는 API 계층입니다.
