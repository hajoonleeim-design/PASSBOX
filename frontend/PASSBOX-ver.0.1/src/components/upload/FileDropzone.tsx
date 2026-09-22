import { useRef, type DragEvent } from 'react'
import { Button } from '../common/Button'

const acceptedFileTypes = '.hwpx,.pdf,.pptx,.xlsx,.md,.txt'

export function FileDropzone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    onFiles(Array.from(event.dataTransfer.files))
  }

  return (
    <div className="file-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        multiple
        accept={acceptedFileTypes}
        onChange={(event) => {
          onFiles(Array.from(event.target.files ?? []))
          event.target.value = ''
        }}
      />
      <span className="file-dropzone__icon" aria-hidden="true">⇧</span>
      <h2>문서를 끌어 놓으세요</h2>
      <p>또는 파일 선택으로 여러 문서를 추가할 수 있습니다.</p>
      <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
        파일 선택
      </Button>
      <small>파일 형식 검사는 사용자 안내용입니다. 업로드 후 서버 검증이 필요합니다.</small>
    </div>
  )
}
