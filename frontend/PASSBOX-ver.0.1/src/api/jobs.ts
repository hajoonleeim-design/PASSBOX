import { apiClient } from './client'
import type { AnalysisJob, CreateJobInput, RetryJobResult } from '../types/security'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

interface BackendJobResponse {
  job_id: number
  request_id: number
  document_id: number
  file_name: string
  extension: string
  size: number
  status: string
  current_step: string
  progress: number
  created_at: string
  updated_at: string
  can_cancel: boolean
  failure_message?: string | null
}

function mapJob(data: BackendJobResponse): AnalysisJob {
  return {
    jobId: String(data.job_id),
    requestId: String(data.request_id),
    documentId: data.document_id,
    file: { fileName: data.file_name, extension: data.extension, size: data.size },
    status: data.status as AnalysisJob['status'],
    currentStep: data.current_step,
    progress: data.progress,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    canCancel: data.can_cancel,
    failureMessage: data.failure_message ?? undefined,
  }
}

export async function createJob(input: CreateJobInput): Promise<AnalysisJob> {
  if (useMock) {
    const { mockCreateJob } = await import('../mocks/jobs')
    return mockCreateJob(input)
  }
  if (!input.documentId) throw new Error('DOCUMENT_ID_MISSING')
  const { data } = await apiClient.post<BackendJobResponse>('/jobs', { document_id: input.documentId })
  return mapJob(data)
}

export async function getJob(jobId: string): Promise<AnalysisJob> {
  if (useMock) {
    const { mockGetJob } = await import('../mocks/jobs')
    return mockGetJob(jobId)
  }
  const { data } = await apiClient.get<BackendJobResponse>(`/jobs/${jobId}`)
  return mapJob(data)
}

export async function cancelJob(jobId: string): Promise<AnalysisJob> {
  if (useMock) {
    const { mockCancelJob } = await import('../mocks/jobs')
    return mockCancelJob(jobId)
  }
  const { data } = await apiClient.post<BackendJobResponse>(`/jobs/${jobId}/cancel`)
  return mapJob(data)
}

export async function retryJob(jobId: string): Promise<RetryJobResult> {
  if (useMock) {
    const { mockRetryJob } = await import('../mocks/jobs')
    return { job: await mockRetryJob(jobId) }
  }
  const { data } = await apiClient.post<BackendJobResponse>(`/jobs/${jobId}/retry`)
  return { job: mapJob(data) }
}
