import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import analysisStartExample from '../../assets/onboarding-upload-analysis-example.png'
import { getUploadPolicyHint, uploadDocument } from '../../api/upload'
import { createJob } from '../../api/jobs'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { PageOnboardingTour, type OnboardingTourStep } from '../../components/common/PageOnboardingTour'
import { EmptyState } from '../../components/common/StateViews'
import { StatusBadge, type StatusLabel } from '../../components/common/StatusBadge'
import { FileDropzone } from '../../components/upload/FileDropzone'
import { useUploadDraft } from '../../stores/useUploadDraft'
import type { UploadDraftRow } from '../../stores/uploadDraftContext'
import type { HashStatus, UploadFileResult, UploadPolicyHint, UploadStatus } from '../../types/upload'
import { createId } from '../../utils/id'

const acceptedExtensions = new Set([
  'hwp', 'hwpx', 'pdf', 'pptx', 'xlsx', 'docx', 'md', 'txt', 'csv', 'html', 'htm',
])
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

const uploadOnboardingSteps: OnboardingTourStep[] = [
  {
    id: 'file-picker',
    target: '[data-onboarding-target="upload-file-picker"]',
    title: '파일을 선택하세요',
    description: '문서를 끌어놓거나 파일 선택 버튼을 눌러 업로드할 파일을 추가합니다.',
  },
  {
    id: 'validation-request',
    target: '[data-onboarding-target="upload-analysis-area"]',
    title: '업로드와 검증이 시작됩니다',
    description: '파일을 추가하면 업로드와 서버 검증이 자동으로 시작됩니다.',
  },
  {
    id: 'analysis-start',
    target: '[data-onboarding-target="upload-analysis-example"]',
    title: '검증 완료 후 분석을 시작하세요',
    description: '검증이 완료되면 파일 행의 분석 시작 버튼을 눌러 분석 Job을 생성합니다.',
  },
]

export function UploadPage() {
  const { files, setFiles } = useUploadDraft()
  const [error, setError] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [isStartingAnalysis, setIsStartingAnalysis] = useState(false)
  const [activeOnboardingStep, setActiveOnboardingStep] = useState<number | null>(null)
  const [policyHint, setPolicyHint] = useState<UploadPolicyHint>({
    allowedExtensions: Array.from(acceptedExtensions),
    maxFileSizeText: '서버 정책에 따라 제한됩니다.',
    maxFileCountText: '서버 정책에 따라 제한됩니다.',
  })
  const navigate = useNavigate()
  const fileListRef = useRef<HTMLDivElement>(null)

  function restartUploadOnboarding() {
    window.dispatchEvent(new CustomEvent('passbox:onboarding-restart', {
      detail: 'passbox:onboarding:upload:v1',
    }))
  }

  useEffect(() => {
    void getUploadPolicyHint().then(setPolicyHint).catch(() => undefined)
  }, [])

  function addFiles(selected: File[]) {
    setError('')
    const next = selected.map((file): UploadDraftRow => {
      const extension = extensionOf(file)
      const allowed = acceptedExtensions.has(extension)
      return {
        id: createId(),
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
    requestAnimationFrame(() => fileListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))

    const uploadable = next.filter((item) => item.uploadStatus === 'PENDING')
    if (uploadable.length > 0) {
      void uploadFiles(uploadable)
    }
  }

  function updateFile(id: string, patch: Partial<UploadDraftRow>) {
    setFiles((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item))
  }

  async function uploadOne(item: UploadDraftRow) {
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

  async function uploadFiles(pending: UploadDraftRow[]) {
    if (pending.length === 0) {
      setError('업로드할 수 있는 대기 파일이 없습니다.')
      return
    }
    setError('')
    setIsUploading(true)
    await Promise.all(pending.map(uploadOne))
    setIsUploading(false)
  }

  async function uploadAll() {
    await uploadFiles(files.filter((item) => item.uploadStatus === 'PENDING'))
  }

  async function startAnalysis(item: UploadDraftRow) {
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
      setFiles((current) => current.map((candidate) => candidate.id === item.id ? { ...candidate, analysisJobId: job.jobId } : candidate))
      navigate(`/analysis/${job.jobId}`)
    } catch {
      setError('분석 작업을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    }
  }

  async function startSingleAnalysis(item: UploadDraftRow) {
    if (isStartingAnalysis) return
    setIsStartingAnalysis(true)
    await startAnalysis(item)
    setIsStartingAnalysis(false)
  }

  async function startAllAnalysis() {
    const eligible = files.filter((item) => item.validationStatus === 'VALIDATED' && item.documentId && !item.analysisJobId)
    if (eligible.length === 0) {
      setError('일괄 분석을 시작할 수 있는 검증 완료 문서가 없습니다.')
      return
    }

    setError('')
    setIsStartingAnalysis(true)
    const results = await Promise.all(eligible.map(async (item) => {
      try {
        const job = await createJob({
          documentId: item.documentId,
          file: { fileName: item.file.name, extension: item.extension, size: item.file.size },
        })
        setFiles((current) => current.map((candidate) => candidate.id === item.id ? { ...candidate, analysisJobId: job.jobId } : candidate))
        return { item, jobId: job.jobId }
      } catch {
        return { item, jobId: null }
      }
    }))
    setIsStartingAnalysis(false)

    const created = results.filter((result): result is { item: UploadDraftRow; jobId: string } => result.jobId !== null)
    const failed = results.filter((result) => result.jobId === null)
    if (failed.length > 0) {
      const failedNames = failed.map((result) => result.item.file.name).join(', ')
      setError(`${created.length}개 문서의 분석 작업을 시작했고, ${failed.length}개는 실패했습니다: ${failedNames}. 실패한 문서는 다시 시도할 수 있습니다.`)
      return
    }
    // 파일 하나만 분석을 시작했을 땐 30건짜리 전체 목록 대신 그 작업 상세 화면으로 바로 이동한다.
    navigate(created.length === 1 ? `/analysis/${created[0].jobId}` : '/analysis/recent')
  }

  const analyzableFiles = files.filter((item) => item.validationStatus === 'VALIDATED' && item.documentId && !item.analysisJobId)
  const isValidationPending = files.some((item) => item.uploadStatus === 'PENDING' || item.uploadStatus === 'UPLOADING' || item.validationStatus === 'PENDING' || item.validationStatus === 'VALIDATING')

  const columns: DataTableColumn<UploadDraftRow>[] = [
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
        {item.validationStatus === 'VALIDATED' && !item.analysisJobId && <Button size="sm" disabled={isStartingAnalysis} onClick={() => void startSingleAnalysis(item)}>분석 시작</Button>}
        {item.analysisJobId && <Link className="table-link" to={`/analysis/${item.analysisJobId}`}>분석 보기</Link>}
        <Button size="sm" variant="ghost" aria-label={`${item.file.name} 제거`} disabled={item.uploadStatus === 'UPLOADING'} onClick={() => setFiles((current) => current.filter((candidate) => candidate.id !== item.id))}>제거</Button>
      </span>,
    },
  ]

  return <section>
    <p className="eyebrow">파일 보안 검사</p>
    <h1>문서 업로드</h1>
    <p>문서를 추가하면 서버 정책에 따라 파일 signature, MIME, 확장자, 크기, 무결성을 검증합니다.</p>
    <Button className="onboarding-restart-button" size="sm" variant="ghost" onClick={restartUploadOnboarding}>사용 안내 다시 보기</Button>
    <div className="upload-layout">
      <FileDropzone files={files} isUploading={isUploading} onFiles={addFiles} onRemove={(id) => setFiles((current) => current.filter((item) => item.id !== id))} />
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
    {error && <div className="section-gap"><Alert variant="danger" title="작업 확인 필요">{error}</Alert></div>}
    <div ref={fileListRef} className="section-heading" data-onboarding-target="upload-analysis-area">
      <div><h2>업로드 및 검증 결과</h2><p>{isValidationPending ? '모든 파일의 업로드와 검증이 끝나면 분석을 시작할 수 있습니다.' : `일괄 분석 가능한 검증 완료 문서 ${analyzableFiles.length}개`}</p></div>
      <div className="upload-result-actions">
        {files.some((item) => item.uploadStatus === 'PENDING') && <Button data-onboarding-target="upload-validation-request" onClick={() => void uploadAll()} disabled={isUploading}>대기 파일 검증 시작</Button>}
        <Button onClick={() => void startAllAnalysis()} disabled={isStartingAnalysis || isUploading || isValidationPending || analyzableFiles.length === 0}>
          {isStartingAnalysis ? '분석 작업 생성 중…' : '분석 시작'}
        </Button>
      </div>
    </div>
    {activeOnboardingStep === 2 && (
      <Card className="upload-onboarding-example">
        <div className="upload-onboarding-example__frame" data-onboarding-target="upload-analysis-example">
          <img src={analysisStartExample} alt="검증 완료 파일 행의 분석 시작 버튼 예시" />
          <span className="upload-onboarding-example__analysis-button" aria-hidden="true" />
        </div>
        <p>온보딩 예시 · 실제 파일이 추가되거나 저장되지는 않습니다.</p>
      </Card>
    )}
    {activeOnboardingStep !== 2 && (files.length === 0 ? <Card><EmptyState label="선택한 파일이 없습니다. 파일을 끌어 놓거나 파일 선택 버튼을 사용해 주세요." /></Card> : <DataTable columns={columns} rows={files} />)}
    <PageOnboardingTour
      storageKey="passbox:onboarding:upload:v1"
      steps={uploadOnboardingSteps}
      onActiveStepChange={setActiveOnboardingStep}
      targetReadyKey={activeOnboardingStep}
    />
  </section>
}
