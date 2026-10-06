import type { UploadFileResult, UploadPolicyHint } from '../types/upload'

export const mockUploadPolicy: UploadPolicyHint = {
  allowedExtensions: ['HWPX', 'PDF', 'PPTX', 'XLSX', 'DOCX', 'MD', 'TXT', 'CSV', 'HTML'],
  maxFileSizeText: '서버 정책에 따라 제한됩니다.',
  maxFileCountText: '서버 정책에 따라 제한됩니다.',
}

let nextMockDocumentId = 1001

export async function mockUploadDocument(file: File): Promise<UploadFileResult> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 450))

  return {
    uploadId: crypto.randomUUID(),
    documentId: nextMockDocumentId++,
    fileName: file.name,
    uploadStatus: 'UPLOADED',
    validationStatus: 'VALIDATED',
    hashStatus: 'COMPLETED',
    message: 'Mock 업로드와 서버 검증이 완료되었습니다.',
  }
}
