import { apiClient } from './client'

export interface SecurityScanResult {
  scanId: number
  documentId: number
  status: string
  totalFindings: number
  highSeverityCount: number
  categories: string[]
  classificationReady: boolean
  createdAt: string
}

interface BackendSecurityScanResponse {
  scan_id: number
  document_id: number
  status: string
  total_findings: number
  high_severity_count: number
  categories: string[]
  classification_ready: boolean
  created_at: string
}

export async function scanDocument(documentId: number): Promise<SecurityScanResult> {
  const { data } = await apiClient.post<BackendSecurityScanResponse>(`/documents/${documentId}/scan`)
  return {
    scanId: data.scan_id,
    documentId: data.document_id,
    status: data.status,
    totalFindings: data.total_findings,
    highSeverityCount: data.high_severity_count,
    categories: data.categories,
    classificationReady: data.classification_ready,
    createdAt: data.created_at,
  }
}
