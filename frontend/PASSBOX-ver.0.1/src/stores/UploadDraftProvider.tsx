import { useState, type PropsWithChildren } from 'react'
import { UploadDraftContext } from './uploadDraftContext'
import type { UploadDraftRow } from './uploadDraftContext'

export function UploadDraftProvider({ children }: PropsWithChildren) {
  const [files, setFiles] = useState<UploadDraftRow[]>([])

  return <UploadDraftContext.Provider value={{ files, setFiles }}>
    {children}
  </UploadDraftContext.Provider>
}
