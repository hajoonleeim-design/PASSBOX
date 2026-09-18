export type UploadStatus = 'PENDING' | 'UPLOADING' | 'UPLOADED' | 'VALIDATING' | 'VALIDATED' | 'FAILED' | 'BLOCKED'
export type HashStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface UploadFileResult {
  uploadId: string
  documentId?: number
  fileName: string
  uploadStatus: UploadStatus
  validationStatus: UploadStatus
  hashStatus: HashStatus
  message?: string
}

export interface UploadPolicyHint {
  allowedExtensions: string[]
  maxFileSizeText: string
  maxFileCountText: string
}
// 업로드 화면과 업로드 API가 주고받는 파일 상태 및 정책 안내의 데이터 모양입니다.
