import type { PolicyActor, PolicyChangeHistory, SecurityPolicy, UpdatePolicyInput } from '../types/policy'
import { apiClient } from './client'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

interface BackendPolicy {
  policy_id: string
  institution_id: string
  version: string
  status: SecurityPolicy['status']
  effective_at: string
  updated_at: string
  updated_by: string
  cso_rules: Array<{ rule_id: string; rule_name: string; detection_type: string; grade: SecurityPolicy['csoRules'][number]['grade']; enabled: boolean; description: string }>
  approval_policy: { s_grade_requires_approval: boolean; approver_roles: SecurityPolicy['approvalPolicy']['approverRoles']; c_grade_approvable: boolean; o_grade_requires_approval: boolean }
  model_allowlist: Array<{ model_id: string; model_name: string; provider: string; enabled: boolean; description: string }>
  retention_policy: { audit_days: number; evidence_days: number; incident_days: number }
  detection_patterns: Array<{ pattern_id: string; pattern_name: string; detection_type: string; enabled: boolean; severity: SecurityPolicy['detectionPatterns'][number]['severity']; description: string }>
}

interface BackendHistory {
  history_id: string
  policy_id: string
  version_before: string
  version_after: string
  changed_by: string
  actor_role: string
  changed_at: string
  change_reason: string
  changed_fields: string[]
  before_value: string
  after_value: string
}

const endpoint = (policyId: string) => `/admin/policies/${encodeURIComponent(policyId)}`

function mapPolicy(data: BackendPolicy): SecurityPolicy {
  return {
    policyId: data.policy_id,
    institutionId: data.institution_id,
    version: data.version,
    status: data.status,
    effectiveAt: data.effective_at,
    updatedAt: data.updated_at,
    updatedBy: data.updated_by,
    csoRules: data.cso_rules.map((item) => ({
      ruleId: item.rule_id,
      ruleName: item.rule_name,
      detectionType: item.detection_type,
      grade: item.grade,
      enabled: item.enabled,
      description: item.description,
    })),
    approvalPolicy: {
      sGradeRequiresApproval: data.approval_policy.s_grade_requires_approval,
      approverRoles: data.approval_policy.approver_roles,
      cGradeApprovable: data.approval_policy.c_grade_approvable,
      oGradeRequiresApproval: data.approval_policy.o_grade_requires_approval,
    },
    modelAllowlist: data.model_allowlist.map((item) => ({
      modelId: item.model_id,
      modelName: item.model_name,
      provider: item.provider,
      enabled: item.enabled,
      description: item.description,
    })),
    retentionPolicy: {
      auditDays: data.retention_policy.audit_days,
      evidenceDays: data.retention_policy.evidence_days,
      incidentDays: data.retention_policy.incident_days,
    },
    detectionPatterns: data.detection_patterns.map((item) => ({
      patternId: item.pattern_id,
      patternName: item.pattern_name,
      detectionType: item.detection_type,
      enabled: item.enabled,
      severity: item.severity,
      description: item.description,
    })),
  }
}

function toBackendPolicy(policy: SecurityPolicy) {
  return {
    policy_id: policy.policyId,
    institution_id: policy.institutionId,
    version: policy.version,
    status: policy.status,
    effective_at: policy.effectiveAt,
    updated_at: policy.updatedAt,
    updated_by: policy.updatedBy,
    cso_rules: policy.csoRules.map((item) => ({
      rule_id: item.ruleId,
      rule_name: item.ruleName,
      detection_type: item.detectionType,
      grade: item.grade,
      enabled: item.enabled,
      description: item.description,
    })),
    approval_policy: {
      s_grade_requires_approval: policy.approvalPolicy.sGradeRequiresApproval,
      approver_roles: policy.approvalPolicy.approverRoles,
      c_grade_approvable: policy.approvalPolicy.cGradeApprovable,
      o_grade_requires_approval: policy.approvalPolicy.oGradeRequiresApproval,
    },
    model_allowlist: policy.modelAllowlist.map((item) => ({
      model_id: item.modelId,
      model_name: item.modelName,
      provider: item.provider,
      enabled: item.enabled,
      description: item.description,
    })),
    retention_policy: {
      audit_days: policy.retentionPolicy.auditDays,
      evidence_days: policy.retentionPolicy.evidenceDays,
      incident_days: policy.retentionPolicy.incidentDays,
    },
    detection_patterns: policy.detectionPatterns.map((item) => ({
      pattern_id: item.patternId,
      pattern_name: item.patternName,
      detection_type: item.detectionType,
      enabled: item.enabled,
      severity: item.severity,
      description: item.description,
    })),
  }
}

function mapHistory(data: BackendHistory): PolicyChangeHistory {
  return {
    historyId: data.history_id,
    policyId: data.policy_id,
    versionBefore: data.version_before,
    versionAfter: data.version_after,
    changedBy: data.changed_by,
    actorRole: data.actor_role as PolicyChangeHistory['actorRole'],
    changedAt: data.changed_at,
    changeReason: data.change_reason,
    changedFields: data.changed_fields,
    beforeValue: data.before_value,
    afterValue: data.after_value,
  }
}

export async function getPolicy(policyId: string, actor: PolicyActor): Promise<SecurityPolicy> {
  if (useMock) {
    const { mockGetPolicy } = await import('../mocks/policy')
    return mockGetPolicy(policyId, actor)
  }
  const { data } = await apiClient.get<BackendPolicy>(endpoint(policyId))
  return mapPolicy(data)
}

export async function getPolicyHistory(policyId: string, actor: PolicyActor): Promise<PolicyChangeHistory[]> {
  if (useMock) {
    const { mockGetPolicyHistory } = await import('../mocks/policy')
    return mockGetPolicyHistory(policyId, actor)
  }
  const { data } = await apiClient.get<BackendHistory[]>(`${endpoint(policyId)}/history`)
  return data.map(mapHistory)
}

export async function updatePolicy(policyId: string, input: UpdatePolicyInput): Promise<SecurityPolicy> {
  if (useMock) {
    const { mockUpdatePolicy } = await import('../mocks/policy')
    return mockUpdatePolicy(policyId, input)
  }
  const { data } = await apiClient.put<BackendPolicy>(endpoint(policyId), {
    policy: toBackendPolicy(input.policy),
    change_reason: input.changeReason,
  })
  return mapPolicy(data)
}

// 정책 조회·수정은 개발 mock과 동일한 화면 계약을 유지하면서 실제 백엔드로 전환됩니다.
