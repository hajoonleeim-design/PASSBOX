export type SecurityGrade = 'C' | 'S' | 'O'

export type JobStatus =
  | 'RECEIVED' | 'INSPECTING' | 'PARSING' | 'DETECTING' | 'CLASSIFICATION_REVIEW' | 'MASKING'
  | 'WAITING_APPROVAL' | 'TRANSMITTING' | 'POST_INSPECTING'
  | 'COMPLETED' | 'BLOCKED' | 'FAILED' | 'CANCELLED' | 'UNKNOWN'

export interface JobFileInfo {
  fileName: string
  extension: string
  size: number
}

export interface AnalysisJob {
  jobId: string
  requestId?: string
  documentId?: number
  file: JobFileInfo
  status: JobStatus
  currentStep: string
  progress: number
  createdAt: string
  updatedAt: string
  canCancel: boolean
  failureMessage?: string
}

export interface CreateJobInput { file: JobFileInfo; documentId?: number }
export interface RetryJobResult { job: AnalysisJob }
// 문서 분석 작업(Job)과 보안 등급에 사용하는 공통 데이터 모양을 정의합니다.
