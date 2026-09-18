import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUploadPolicyHint, uploadDocument } from '../../api/upload'
import { createJob } from '../../api/jobs'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { EmptyState } from '../../components/common/StateViews'
import { StatusBadge, type StatusLabel } from '../../components/common/StatusBadge'
import { FileDropzone } from '../../components/upload/FileDropzone'
import type { HashStatus, UploadFileResult, UploadPolicyHint, UploadStatus } from '../../types/upload'

interface UploadRow {
  id: string
  file: File
  extension: string
  documentId?: number
  uploadStatus: UploadStatus
  validationStatus: UploadStatus
  hashStatus: HashStatus
  message?: string
}

const acceptedExtensions = new Set(['hwp', 'hwpx', 'pdf', 'ppt', 'pptx', 'xls', 'xlsx'])
const statusLabels: Record<UploadStatus, StatusLabel> = {
  PENDING: '대기',
  UPLOADING: '업로드 중',
  UPLOADED: '업로드 완료',
  VALIDATING: '검증 중',
  VALIDATED: '검증 완료',
  FAILED: '실패',
  BLOCKED: '차단',
}
const hashLabels: Record<HashStatus, string> = {
  PENDING: '계산 대기',
  PROCESSING: '계산 중',
  COMPLETED: '계산 완료',
  FAILED: '계산 실패',
}
const formatSize = (size: number) => `${(size / 1024 / 1024).toFixed(size < 1024 * 1024 ? 2 : 1)} MB`
const extensionOf = (file: File) => file.name.split('.').pop()?.toLowerCase() ?? ''

export function UploadPage() {
  const [files, setFiles] = useState<UploadRow[]>([])
  const [error, setError] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [policyHint, setPolicyHint] = useState<UploadPolicyHint>({
    allowedExtensions: Array.from(acceptedExtensions),
    maxFileSizeText: '서버 정책에 따라 제한됩니다.',
    maxFileCountText: '서버 정책에 따라 제한됩니다.',
  })
  const navigate = useNavigate()

  useEffect(() => {
    void getUploadPolicyHint().then(setPolicyHint).catch(() => undefined)
  }, [])

  function addFiles(selected: File[]) {
    setError('')
    const next = selected.map((file): UploadRow => {
      const extension = extensionOf(file)
      const allowed = acceptedExtensions.has(extension)
      return {
        id: crypto.randomUUID(),
        file,
        extension: extension ? extension.toUpperCase() : '없음',
        uploadStatus: allowed ? 'PENDING' : 'FAILED',
        validationStatus: allowed ? 'PENDING' : 'FAILED',
        hashStatus: allowed ? 'PENDING' : 'FAILED',
        message: allowed ? undefined : '지원하지 않는 파일 형식입니다.',
      }
    })
    setFiles((current) => [...current, ...next])
    if (next.some((item) => item.uploadStatus === 'FAILED')) {
      setError('지원하지 않는 파일 형식이 포함되어 있습니다. 허용 형식을 확인해 주세요.')
    }
  }

  function updateFile(id: string, patch: Partial<UploadRow>) {
    setFiles((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item))
  }

  async function uploadOne(item: UploadRow) {
    updateFile(item.id, {
      uploadStatus: 'UPLOADING',
      validationStatus: 'VALIDATING',
      hashStatus: 'PROCESSING',
      message: '업로드 및 서버 검증을 요청하는 중입니다.',
    })
    try {
      const result: UploadFileResult = await uploadDocument(item.file)
      updateFile(item.id, {
        documentId: result.documentId,
        uploadStatus: result.uploadStatus,
        validationStatus: result.validationStatus,
        hashStatus: result.hashStatus,
        message: result.message,
      })
    } catch {
      updateFile(item.id, {
        uploadStatus: 'FAILED',
        validationStatus: 'FAILED',
        hashStatus: 'FAILED',
        message: '업로드에 실패했습니다. 네트워크 연결 또는 서버 상태를 확인해 주세요.',
      })
    }
  }

  async function uploadAll() {
    const pending = files.filter((item) => item.uploadStatus === 'PENDING')
    if (pending.length === 0) {
      setError('업로드할 수 있는 대기 파일이 없습니다.')
      return
    }
    setError('')
    setIsUploading(true)
    await Promise.all(pending.map(uploadOne))
    setIsUploading(false)
  }

  async function startAnalysis(item: UploadRow) {
    if (!item.documentId) {
      setError('서버 문서 ID가 없습니다. 파일을 먼저 검증해 주세요.')
      return
    }
    try {
      setError('')
      const job = await createJob({
        documentId: item.documentId,
        file: { fileName: item.file.name, extension: item.extension, size: item.file.size },
      })
      navigate(`/analysis/${job.jobId}`)
    } catch {
      setError('분석 작업을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    }
  }

  const columns: DataTableColumn<UploadRow>[] = [
    {
      key: 'name',
      header: '파일명',
      render: (item) => <><strong>{item.file.name}</strong>{item.message && <small className="table-note">{item.message}</small>}</>,
    },
    { key: 'extension', header: '확장자', render: (item) => item.extension },
    { key: 'size', header: '크기', render: (item) => formatSize(item.file.size) },
    { key: 'upload', header: '업로드 상태', render: (item) => <StatusBadge label={statusLabels[item.uploadStatus]} /> },
    { key: 'validation', header: '검증 상태', render: (item) => <StatusBadge label={statusLabels[item.validationStatus]} /> },
    { key: 'hash', header: '해시 상태', render: (item) => hashLabels[item.hashStatus] },
    {
      key: 'manage',
      header: '관리',
      render: (item) => <span className="table-actions">
        {item.validationStatus === 'VALIDATED' && <Button size="sm" onClick={() => void startAnalysis(item)}>분석 시작</Button>}
        <Button size="sm" variant="ghost" aria-label={`${item.file.name} 제거`} disabled={item.uploadStatus === 'UPLOADING'} onClick={() => setFiles((current) => current.filter((candidate) => candidate.id !== item.id))}>제거</Button>
      </span>,
    },
  ]

  return <section>
    <p className="eyebrow">DOCUMENT SECURITY CHECK</p>
    <h1>문서 업로드</h1>
    <p>문서를 추가하면 서버 정책에 따라 파일 signature, MIME, 확장자, 크기, 무결성을 검증합니다.</p>
    <div className="upload-layout">
      <FileDropzone onFiles={addFiles} />
      <Card className="upload-policy">
        <h2>업로드 전 안내</h2>
        <dl>
          <div><dt>허용 파일</dt><dd>{policyHint.allowedExtensions.join(' / ')}</dd></div>
          <div><dt>최대 파일 크기</dt><dd>{policyHint.maxFileSizeText}</dd></div>
          <div><dt>최대 파일 개수</dt><dd>{policyHint.maxFileCountText}</dd></div>
        </dl>
        <Alert variant="info" title="서버 검증 필요">브라우저의 확장자 확인은 사용자 안내용이며, 보안 검증 결과가 아닙니다.</Alert>
      </Card>
    </div>
    {error && <div className="section-gap"><Alert variant="danger" title="업로드 확인 필요">{error}</Alert></div>}
    <div className="section-heading">
      <div><h2>선택한 파일</h2><p>각 파일은 독립적으로 업로드 및 검증됩니다.</p></div>
      <Button onClick={() => void uploadAll()} disabled={isUploading || files.length === 0}>{isUploading ? '업로드 중' : '검증 요청'}</Button>
    </div>
    {files.length === 0 ? <Card><EmptyState label="선택한 파일이 없습니다. 파일을 끌어 놓거나 파일 선택 버튼을 사용해 주세요." /></Card> : <DataTable columns={columns} rows={files} />}
  </section>
}
