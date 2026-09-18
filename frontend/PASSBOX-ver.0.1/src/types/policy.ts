import type { UserRole } from './auth'
import type { SecurityGrade } from './security'
export type PolicyStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE'
export interface CsoRule { ruleId: string; ruleName: string; detectionType: string; grade: SecurityGrade; enabled: boolean; description: string }
export interface ApprovalPolicy { sGradeRequiresApproval: boolean; approverRoles: UserRole[]; cGradeApprovable: boolean; oGradeRequiresApproval: boolean }
export interface ModelAllowlistEntry { modelId: string; modelName: string; provider: string; enabled: boolean; description: string }
export interface RetentionPolicy { auditDays: number; evidenceDays: number; incidentDays: number }
export interface DetectionPattern { patternId: string; patternName: string; detectionType: string; enabled: boolean; severity: 'LOW' | 'MEDIUM' | 'HIGH'; description: string }
export interface SecurityPolicy { policyId: string; institutionId: string; version: string; status: PolicyStatus; effectiveAt: string; updatedAt: string; updatedBy: string; csoRules: CsoRule[]; approvalPolicy: ApprovalPolicy; modelAllowlist: ModelAllowlistEntry[]; retentionPolicy: RetentionPolicy; detectionPatterns: DetectionPattern[] }
export interface PolicyActor { userId: string; displayName: string; role: UserRole }
export interface PolicyChangeHistory { historyId: string; policyId: string; versionBefore: string; versionAfter: string; changedBy: string; actorRole: UserRole; changedAt: string; changeReason: string; changedFields: string[]; beforeValue: string; afterValue: string }
export interface UpdatePolicyInput { policy: SecurityPolicy; changeReason: string; actor: PolicyActor }
// 보안 정책의 현재 값과 버전별 스냅샷에 사용하는 데이터 모양입니다.
