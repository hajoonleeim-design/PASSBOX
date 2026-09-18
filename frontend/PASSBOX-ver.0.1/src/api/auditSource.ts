import type { AuditActor, AuditEvidence, AuditPdfResult, AuditRecord } from '../types/audit'
import { apiClient } from './client'
import { generateAuditPdf as generateMockAuditPdf, getAudit as getMockAudit, getAuditEvidence as getMockAuditEvidence } from './audit'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

interface BackendAuditRecord {
  request_id: string
  job_id: string | null
  grade: AuditRecord['grade']
  policy_version: string
  current_status: string
  created_at: string
  completed_at: string | null
  incident_id: string | null
  events: Array<{
    event_id: string
    event_type: AuditRecord['events'][number]['eventType']
    status: string
    actor: string
    actor_role: string
    timestamp: string
    description: string
    metadata?: Record<string, string>
  }>
  evidence: {
    file_name: string
    file_size: string
    file_hash: string
    file_type: string
    request_id: string
    job_id: string | null
    grade: AuditEvidence['grade']
    detection_type: string | null
    policy_version: string
    approval_status: AuditEvidence['approvalStatus']
    post_inspection_status: AuditEvidence['postInspectionStatus'] | null
    incident_id: string | null
  }
  approval_history: Array<{
    id: string
    action: 'APPROVED' | 'REJECTED'
    actor: { user_id: string; display_name: string; role: string }
    acted_at: string
    reason: string | null
  }>
}

const toRequestNumber = (requestId: string) => {
  const value = Number(requestId)
  if (!Number.isInteger(value) || value < 1) throw new Error('NOT_FOUND')
  return value
}

function mapAudit(data: BackendAuditRecord): AuditRecord {
  return {
    requestId: data.request_id,
    jobId: data.job_id ?? undefined,
    grade: data.grade,
    policyVersion: data.policy_version,
    currentStatus: data.current_status,
    createdAt: data.created_at,
    completedAt: data.completed_at ?? undefined,
    incidentId: data.incident_id ?? undefined,
    events: data.events.map((event) => ({
      eventId: event.event_id,
      eventType: event.event_type,
      status: event.status,
      actor: event.actor,
      actorRole: event.actor_role as AuditRecord['events'][number]['actorRole'],
      timestamp: event.timestamp,
      description: event.description,
      metadata: event.metadata,
    })),
    evidence: {
      fileName: data.evidence.file_name,
      fileSize: data.evidence.file_size,
      fileHash: data.evidence.file_hash,
      fileType: data.evidence.file_type,
      requestId: data.evidence.request_id,
      jobId: data.evidence.job_id ?? undefined,
      grade: data.evidence.grade,
      detectionType: data.evidence.detection_type ?? undefined,
      policyVersion: data.evidence.policy_version,
      approvalStatus: data.evidence.approval_status,
      postInspectionStatus: data.evidence.post_inspection_status ?? undefined,
      incidentId: data.evidence.incident_id ?? undefined,
    },
    approvalHistory: data.approval_history.map((item) => ({
      id: item.id,
      action: item.action,
      actor: {
        userId: item.actor.user_id,
        displayName: item.actor.display_name,
        role: item.actor.role as AuditRecord['approvalHistory'][number]['actor']['role'],
      },
      actedAt: item.acted_at,
      reason: item.reason ?? undefined,
    })),
  }
}

export async function getAuditSource(requestId: string, actor: AuditActor): Promise<AuditRecord> {
  if (useMock) return getMockAudit(requestId, actor)
  const { data } = await apiClient.get<BackendAuditRecord>(`/requests/${toRequestNumber(requestId)}/audit`)
  return mapAudit(data)
}

export async function getAuditEvidenceSource(requestId: string, actor: AuditActor): Promise<AuditEvidence> {
  if (useMock) return getMockAuditEvidence(requestId, actor)
  const { data } = await apiClient.get<BackendAuditRecord['evidence']>(`/requests/${toRequestNumber(requestId)}/audit/evidence`)
  return {
    fileName: data.file_name,
    fileSize: data.file_size,
    fileHash: data.file_hash,
    fileType: data.file_type,
    requestId: data.request_id,
    jobId: data.job_id ?? undefined,
    grade: data.grade,
    detectionType: data.detection_type ?? undefined,
    policyVersion: data.policy_version,
    approvalStatus: data.approval_status,
    postInspectionStatus: data.post_inspection_status ?? undefined,
    incidentId: data.incident_id ?? undefined,
  }
}

export async function generateAuditPdfSource(requestId: string, actor: AuditActor): Promise<AuditPdfResult> {
  if (useMock) return generateMockAuditPdf(requestId, actor)
  const { data } = await apiClient.get<Blob>(`/requests/${toRequestNumber(requestId)}/audit.pdf`, {
    responseType: 'blob',
  })
  return { fileName: `audit-${requestId}.pdf`, blob: data }
}
