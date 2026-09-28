import { useContext } from 'react'
import { UploadDraftContext } from './uploadDraftContext'

export function useUploadDraft() {
  const context = useContext(UploadDraftContext)
  if (!context) {
    throw new Error('useUploadDraft must be used inside UploadDraftProvider')
  }
  return context
}
