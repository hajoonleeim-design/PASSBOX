import type { ApprovalHistoryEntry, DecisionStatus } from './decision'
import type { PostInspectionStatus } from './aiChat'
import type { SecurityGrade } from './security'
import type { UserRole } from './auth'

export type AuditEventType = 'REQUEST_CREATED' | 'FILE_VALIDATED' | 'ANALYSIS_STARTED' | 'ANALYSIS_COMPLETED' | 'ANALYSIS_BLOCKED' | 'DECISION_CREATED' | 'APPROVAL_REQUESTED' | 'APPROVED' | 'REJECTED' | 'PAYLOAD_VALIDATED' | 'AI_TRANSMITTED' | 'AI_RESPONSE_RECEIVED' | 'POST_INSPECTION_STARTED' | 'POST_INSPECTION_VERIFIED' | 'POST_INSPECTION_BLOCKED' | 'COMPLETED' | 'FAILED'
export interface AuditEvent { eventId: string; eventType: AuditEventType; status: string; actor: string; actorRole: UserRole | 'SYSTEM'; timestamp: string; description: string; metadata?: Record<string, string> }
export interface AuditEvidence { fileName: string; fileSize: string; fileHash: string; fileType: string; requestId: string; jobId?: string; grade: SecurityGrade; detectionType?: string; policyVersion: string; approvalStatus: DecisionStatus; postInspectionStatus?: PostInspectionStatus; incidentId?: string }
export interface AuditRecord { requestId: string; jobId?: string; grade: SecurityGrade; policyVersion: string; currentStatus: string; createdAt: string; completedAt?: string; incidentId?: string; events: AuditEvent[]; evidence: AuditEvidence; approvalHistory: ApprovalHistoryEntry[] }
export interface AuditActor { userId: string; role: UserRole }
export interface AuditPdfResult { fileName: string; blob: Blob }
// 감사 타임라인과 증적 정보에 쓰이는 데이터 모양을 정의합니다.
