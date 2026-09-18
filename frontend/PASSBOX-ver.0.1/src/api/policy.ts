import type { PolicyActor, PolicyChangeHistory, SecurityPolicy, UpdatePolicyInput } from '../types/policy'
const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL
export async function getPolicy(policyId: string, actor: PolicyActor): Promise<SecurityPolicy> { if (useMock) { const { mockGetPolicy } = await import('../mocks/policy'); return mockGetPolicy(policyId, actor) } throw new Error('승인된 Policy API 명세가 아직 연결되지 않았습니다.') }
export async function getPolicyHistory(policyId: string, actor: PolicyActor): Promise<PolicyChangeHistory[]> { if (useMock) { const { mockGetPolicyHistory } = await import('../mocks/policy'); return mockGetPolicyHistory(policyId, actor) } throw new Error('승인된 Policy API 명세가 아직 연결되지 않았습니다.') }
export async function updatePolicy(policyId: string, input: UpdatePolicyInput): Promise<SecurityPolicy> { if (useMock) { const { mockUpdatePolicy } = await import('../mocks/policy'); return mockUpdatePolicy(policyId, input) } throw new Error('승인된 Policy API 명세가 아직 연결되지 않았습니다.') }
// 보안 정책과 버전 이력을 조회하는 API 계층입니다.
