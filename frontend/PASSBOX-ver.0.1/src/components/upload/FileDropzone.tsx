import { useRef, useState, type DragEvent } from 'react'
import { Button } from '../common/Button'
import type { UploadDraftRow } from '../../stores/uploadDraftContext'

const acceptedFileTypes = '.hwp,.hwpx,.pdf,.pptx,.xlsx,.docx,.md,.txt,.csv,.html,.htm'

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function statusForFile(file: UploadDraftRow) {
  if (file.uploadStatus === 'BLOCKED' || file.validationStatus === 'BLOCKED') {
    return { label: '정책 차단', tone: 'danger' }
  }
  if (file.uploadStatus === 'FAILED') return { label: '업로드 실패', tone: 'danger' }
  if (file.validationStatus === 'FAILED') return { label: '검증 실패', tone: 'danger' }
  if (file.validationStatus === 'VALIDATED') return { label: '검증 완료', tone: 'success' }
  if (file.uploadStatus === 'UPLOADED') return { label: '업로드 완료 · 검증 대기', tone: 'success' }
  if (file.uploadStatus === 'UPLOADING' || file.validationStatus === 'VALIDATING') return { label: '업로드·검증 중', tone: 'info' }
  return { label: '선택 완료 · 전송 전', tone: 'neutral' }
}

export function FileDropzone({
  files = [],
  isUploading = false,
  onFiles,
  onRemove,
}: {
  files: UploadDraftRow[]
  isUploading: boolean
  onFiles: (files: File[]) => void
  onRemove: (id: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    if (!isUploading) onFiles(Array.from(event.dataTransfer.files))
  }

  return (
    <div
      className={`file-dropzone ${files.length > 0 ? 'file-dropzone--has-files' : ''} ${isDragging ? 'file-dropzone--dragging' : ''} ${isUploading ? 'file-dropzone--disabled' : ''}`}
      data-onboarding-target="upload-file-picker"
      aria-busy={isUploading}
      onDragEnter={(event) => { event.preventDefault(); if (!isUploading) setIsDragging(true) }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDragging(false) }}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        multiple
        accept={acceptedFileTypes}
        disabled={isUploading}
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []))
          event.target.value = ''
        }}
      />
      {files.length === 0 ? (
        <>
          <span className="file-dropzone__icon" aria-hidden="true">⇧</span>
          <h2>문서를 끌어 놓으세요</h2>
          <p>또는 파일 선택으로 여러 문서를 추가할 수 있습니다.</p>
          <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
            파일 선택
          </Button>
          <small>파일 형식 검사는 사용자 안내용입니다. 업로드 후 서버 검증이 필요합니다.</small>
        </>
      ) : (
        <div className="file-dropzone__selection">
          <div className="file-dropzone__selection-heading" aria-live="polite">
            <span className={`file-dropzone__selection-mark ${isUploading ? 'is-uploading' : ''}`} aria-hidden="true">
              {isUploading ? <span className="file-dropzone__spinner" /> : '✓'}
            </span>
            <div>
              <h2>{isUploading ? '문서를 업로드하고 검증하고 있습니다' : `문서 ${files.length}개가 추가되었습니다`}</h2>
              <p>{isUploading ? '완료될 때까지 이 화면을 유지해 주세요.' : '파일을 추가하면 업로드와 서버 검증이 자동으로 시작됩니다.'}</p>
            </div>
          </div>
          <ul className="file-dropzone__file-list" aria-label="선택한 파일 목록">
            {files.map((file) => {
              const status = statusForFile(file)
              return (
                <li className="file-dropzone__file" key={file.id}>
                  <span className="file-dropzone__file-type" aria-hidden="true">{file.extension === '없음' ? 'FILE' : file.extension}</span>
                  <span className="file-dropzone__file-info">
                    <strong title={file.file.name}>{file.file.name}</strong>
                    <small>{formatFileSize(file.file.size)}</small>
                    {file.message && <small className="file-dropzone__file-message">{file.message}</small>}
                  </span>
                  <span className={`file-dropzone__status file-dropzone__status--${status.tone}`}>
                    <i aria-hidden="true" />{status.label}
                  </span>
                  <button
                    type="button"
                    className="file-dropzone__remove"
                    aria-label={`${file.file.name} 선택 취소`}
                    disabled={isUploading || file.uploadStatus === 'UPLOADING'}
                    onClick={() => onRemove(file.id)}
                  >
                    ×
                  </button>
                </li>
              )
            })}
          </ul>
          <div className="file-dropzone__selection-footer">
            <Button type="button" variant="secondary" disabled={isUploading} onClick={() => inputRef.current?.click()}>
              파일 추가
            </Button>
            <small>파일을 더 추가하면 업로드와 검증이 바로 시작됩니다.</small>
          </div>
        </div>
      )}
    </div>
  )
}
