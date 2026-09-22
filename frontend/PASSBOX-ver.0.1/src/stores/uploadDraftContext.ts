import { createContext, type Dispatch, type SetStateAction } from 'react'
import type { HashStatus, UploadStatus } from '../types/upload'

export interface UploadDraftRow {
  id: string
  file: File
  extension: string
  documentId?: number
  uploadStatus: UploadStatus
  validationStatus: UploadStatus
  hashStatus: HashStatus
  message?: string
}

export interface UploadDraftContextValue {
  files: UploadDraftRow[]
  setFiles: Dispatch<SetStateAction<UploadDraftRow[]>>
}

export const UploadDraftContext = createContext<UploadDraftContextValue | null>(null)
