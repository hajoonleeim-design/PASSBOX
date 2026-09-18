import { apiClient } from './client'

export interface ExtractionResult {
  textId: number
  documentId: number
  filename: string
  extractor: string
  charCount: number
  truncated: boolean
  preview: string
  status: string
}

interface BackendExtractionResponse {
  text_id: number
  document_id: number
  filename: string
  extractor: string
  char_count: number
  truncated: boolean
  preview: string
  status: string
}

export async function extractDocument(documentId: number): Promise<ExtractionResult> {
  const { data } = await apiClient.post<BackendExtractionResponse>(`/documents/${documentId}/extract`)
  return {
    textId: data.text_id,
    documentId: data.document_id,
    filename: data.filename,
    extractor: data.extractor,
    charCount: data.char_count,
    truncated: data.truncated,
    preview: data.preview,
    status: data.status,
  }
}
