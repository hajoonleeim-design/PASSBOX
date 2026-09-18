import type { SecurityGrade } from './security'

export type ProviderHealth = 'HEALTHY' | 'DEGRADED' | 'DOWN' | 'UNKNOWN'
export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED'

export interface OperationsSummary {
  totalRequests: number
  completedRequests: number
  blockedRequests: number
  failedRequests: number
  processingRequests: number
  successRate: number
  failureRate: number
}

export interface QueueStatus {
  totalQueued: number
  received: number
  inspecting: number
  parsing: number
  detecting: number
  masking: number
  waitingApproval: number
  transmitting: number
  postInspecting: number
}

export interface OperationsPerformance {
  averageProcessingTimeMs: number
  p95ProcessingTimeMs: number
  throughputPerHour: number
}

export interface ProviderStatus {
  providerId: string
  providerName: string
  status: ProviderHealth
  responseTimeMs?: number
  lastCheckedAt: string
  message: string
}

export interface RecentOperationsJob {
  jobId: string
  requestId: string
  fileNameDisplay: string
  status: string
  currentStep: string
  grade: SecurityGrade
  startedAt: string
  updatedAt: string
  processingTimeMs?: number
}

export interface OperationsIncident {
  incidentId: string
  severity: IncidentSeverity
  status: IncidentStatus
  occurredAt: string
  summary: string
  relatedJobId?: string
  resolvedAt?: string
}

export interface CsoDistribution {
  grade: SecurityGrade
  count: number
}

export interface OperationsDashboard {
  generatedAt: string
  summary: OperationsSummary
  queue: QueueStatus
  performance: OperationsPerformance
  providers: ProviderStatus[]
  recentJobs: RecentOperationsJob[]
  csoDistribution: CsoDistribution[]
  incidents: OperationsIncident[]
}
// 운영 대시보드의 수치, 알림, 차트 데이터 모양을 정의합니다.
