import { mockUploadDocument, mockUploadPolicy } from '../mocks/upload'
import { apiClient } from './client'
import type { UploadFileResult, UploadPolicyHint } from '../types/upload'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

export async function getUploadPolicyHint(): Promise<UploadPolicyHint> {
  return mockUploadPolicy
}

export async function uploadDocument(file: File): Promise<UploadFileResult> {
  if (useMock) return mockUploadDocument(file)

  const formData = new FormData()
  formData.append('file', file)

  const { data: uploaded } = await apiClient.post<BackendUploadResponse>('/documents/upload', formData)
  const { data: inspected } = await apiClient.post<BackendInspectResponse>(`/documents/${uploaded.document_id}/inspect`)

  return {
    uploadId: String(uploaded.document_id),
    documentId: uploaded.document_id,
    fileName: uploaded.filename,
    uploadStatus: 'UPLOADED',
    validationStatus: inspected.status === 'READY_FOR_PARSING' ? 'VALIDATED' : 'FAILED',
    hashStatus: 'COMPLETED',
    message: '서버 격리 저장과 기본 안전성 검사가 완료되었습니다.',
  }
}

interface BackendUploadResponse {
  document_id: number
  filename: string
  extension: string
  mime_type: string
  size_bytes: number
  sha256: string
  status: string
}

interface BackendInspectResponse {
  document_id: number
  filename: string
  detected_format: string
  size_bytes: number
  sha256: string
  inspection_result: string
  status: string
}
