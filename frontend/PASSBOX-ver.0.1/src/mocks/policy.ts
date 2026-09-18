import type {
  PolicyActor,
  PolicyChangeHistory,
  SecurityPolicy,
  UpdatePolicyInput,
} from '../types/policy'

const now = () => new Date().toISOString()
const policies = new Map<string, SecurityPolicy>()
// Current policy is kept separately from immutable version snapshots.
const versions = new Map<string, SecurityPolicy[]>()
const histories = new Map<string, PolicyChangeHistory[]>()

const copy = (policy: SecurityPolicy): SecurityPolicy => structuredClone(policy)
const isAdmin = (actor: PolicyActor) => actor.role === 'ADMIN'

const base = (policyId = 'mock-current'): SecurityPolicy => ({
  policyId,
  institutionId: 'DEV-TEST-ORG',
  version: policyId === 'mock-old' ? 'v1.2' : 'v1.3',
  status: 'ACTIVE',
  effectiveAt: now(),
  updatedAt: now(),
  updatedBy: '테스트 관리자',
  csoRules: [
    { ruleId: 'rule-pii', ruleName: '민감정보 형식', detectionType: '개인정보', grade: 'S', enabled: true, description: '민감정보 형식이 확인되면 승인 대상으로 분류합니다.' },
    { ruleId: 'rule-credential', ruleName: '인증정보 형식', detectionType: '인증정보', grade: 'C', enabled: true, description: '인증정보 형식이 확인되면 외부 전송을 차단합니다.' },
    { ruleId: 'rule-general', ruleName: '일반 문서', detectionType: '일반', grade: 'O', enabled: true, description: '정책 검증을 완료한 일반 문서입니다.' },
  ],
  approvalPolicy: {
    sGradeRequiresApproval: true,
    approverRoles: ['APPROVER', 'ADMIN'],
    cGradeApprovable: false,
    oGradeRequiresApproval: false,
  },
  modelAllowlist: [
    { modelId: 'gpt-4o-mini', modelName: 'gpt-4o-mini', provider: 'openai', enabled: true, description: '기관에서 허용한 OpenAI 모델입니다.' },
    { modelId: '*', modelName: '*', provider: 'gemini', enabled: true, description: '기관에서 허용한 Gemini 모델입니다.' },
    { modelId: 'external-model-x', modelName: 'External-Model-X', provider: 'unknown', enabled: false, description: '허용되지 않은 외부 모델 예시입니다.' },
  ],
  retentionPolicy: { auditDays: 365, evidenceDays: 180, incidentDays: 730 },
  detectionPatterns: [
    { patternId: 'pattern-phone', patternName: '연락처 형식', detectionType: '개인정보', enabled: true, severity: 'MEDIUM', description: '가상의 형식 메타데이터입니다.' },
    { patternId: 'pattern-credential', patternName: '인증정보 형식', detectionType: '인증정보', enabled: true, severity: 'HIGH', description: '가상의 형식 메타데이터입니다.' },
  ],
})

function policyFor(policyId: string): SecurityPolicy {
  if (policyId === 'mock-network-error') throw new Error('NETWORK_ERROR')
  if (policyId === 'mock-forbidden') throw new Error('FORBIDDEN')

  let policy = policies.get(policyId)
  if (!policy && ['mock-current', 'mock-old', 'mock-history'].includes(policyId)) {
    policy = base(policyId)
    policies.set(policyId, policy)
    versions.set(policyId, [copy(policy)])
    histories.set(
      policyId,
      policyId === 'mock-history'
        ? [{
            historyId: 'history-1', policyId, versionBefore: 'v1.1', versionAfter: 'v1.2',
            changedBy: '테스트 관리자', actorRole: 'ADMIN', changedAt: now(),
            changeReason: '승인 권한 정책 정비', changedFields: ['approvalPolicy'],
            beforeValue: 'APPROVER', afterValue: 'APPROVER + ADMIN',
          }]
        : [],
    )
  }
  if (!policy) throw new Error('NOT_FOUND')
  return policy
}

export async function mockGetPolicy(policyId: string, actor: PolicyActor) {
  if (!isAdmin(actor)) throw new Error('FORBIDDEN')
  return copy(policyFor(policyId))
}

export async function mockGetPolicyHistory(policyId: string, actor: PolicyActor) {
  if (!isAdmin(actor)) throw new Error('FORBIDDEN')
  policyFor(policyId)
  return structuredClone(histories.get(policyId) ?? [])
}

export async function mockUpdatePolicy(policyId: string, input: UpdatePolicyInput) {
  if (!isAdmin(input.actor)) throw new Error('FORBIDDEN')
  if (!input.changeReason.trim()) throw new Error('INVALID_REASON')

  const previous = policyFor(policyId)
  const fields = ['csoRules', 'approvalPolicy', 'modelAllowlist', 'retentionPolicy', 'detectionPatterns']
    .filter((field) => JSON.stringify(previous[field as keyof SecurityPolicy]) !== JSON.stringify(input.policy[field as keyof SecurityPolicy]))
  if (fields.length === 0) throw new Error('NO_CHANGES')

  const nextNumber = Number(previous.version.replace('v', '')) + 0.1
  const next: SecurityPolicy = {
    ...copy(input.policy),
    policyId,
    version: `v${nextNumber.toFixed(1)}`,
    updatedAt: now(),
    updatedBy: input.actor.displayName,
  }

  policies.set(policyId, next)
  versions.set(policyId, [...(versions.get(policyId) ?? [copy(previous)]), copy(next)])

  const history: PolicyChangeHistory = {
    historyId: crypto.randomUUID(), policyId, versionBefore: previous.version, versionAfter: next.version,
    changedBy: input.actor.displayName, actorRole: input.actor.role, changedAt: now(),
    changeReason: input.changeReason.trim(), changedFields: fields,
    beforeValue: JSON.stringify(fields.reduce((result, key) => ({ ...result, [key]: previous[key as keyof SecurityPolicy] }), {})),
    afterValue: JSON.stringify(fields.reduce((result, key) => ({ ...result, [key]: next[key as keyof SecurityPolicy] }), {})),
  }
  histories.set(policyId, [history, ...(histories.get(policyId) ?? [])])
  return copy(next)
}
// 정책 관리 화면에서 현재 정책과 과거 버전을 보여 주기 위한 가짜 데이터입니다.
