import type { UploadFileResult, UploadPolicyHint } from '../types/upload'

export const mockUploadPolicy: UploadPolicyHint = {
  allowedExtensions: ['HWPX', 'PDF', 'PPTX', 'XLSX', 'MD', 'TXT'],
  maxFileSizeText: '서버 정책에 따라 제한됩니다.',
  maxFileCountText: '서버 정책에 따라 제한됩니다.',
}

export async function mockUploadDocument(file: File): Promise<UploadFileResult> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 450))
  return { uploadId: crypto.randomUUID(), fileName: file.name, uploadStatus: 'UPLOADED', validationStatus: 'VALIDATED', hashStatus: 'COMPLETED', message: '서버 검증 대기 및 Mock 검증이 완료되었습니다.' }
}
// 실제 서버 대신 업로드 결과를 흉내 내는 가짜 구현입니다.
