import type { SecurityGrade } from './security'
import type { UserRole } from './auth'

export type DecisionStatus = 'BLOCKED' | 'WAITING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'ALLOWED' | 'UNKNOWN'
export interface DetectionEvidence { type: string; item: string; policy: string; description: string }
export interface DecisionActor { userId: string; displayName: string; role: UserRole }
export interface ApprovalHistoryEntry { id: string; action: 'APPROVED' | 'REJECTED'; actor: DecisionActor; actedAt: string; reason?: string }
export interface ClassificationDecision {
  requestId: string
  jobId?: string
  fileName: string
  grade: SecurityGrade
  gradeName: string
  description: string
  detections: DetectionEvidence[]
  policyVersion: string
  maskingPreview?: string
  blockReason?: string
  status: DecisionStatus
  createdAt: string
  decidedAt: string
  approvalId?: number
  approval?: ApprovalHistoryEntry
  history: ApprovalHistoryEntry[]
}

export interface RejectDecisionInput { reason: string; actor: DecisionActor }
// 문서 보안 판정, 승인/반려 이력에 쓰이는 데이터 모양을 정의합니다.
