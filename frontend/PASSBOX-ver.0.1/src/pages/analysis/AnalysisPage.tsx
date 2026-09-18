import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  confirmClassification,
  getClassificationDecision,
  getClassificationRecommendation,
  type ClassificationDecision,
  type ClassificationRecommendation,
} from '../../api/classification'
import type { ApiError } from '../../api/client'
import { forwardToGateway, type GatewayForwardResult } from '../../api/gateway'
import { cancelJob, retryJob } from '../../api/jobs'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { ConfirmDialog } from '../../components/common/Modal'
import { ErrorState, LoadingState } from '../../components/common/StateViews'
import { StatusBadge, type StatusLabel } from '../../components/common/StatusBadge'
import { Toast } from '../../components/common/Toast'
import { Stepper } from '../../components/upload/Stepper'
import { isTerminalJob, useJobPolling } from '../../hooks/useJobPolling'
import type { AnalysisJob, JobStatus, SecurityGrade } from '../../types/security'

const statuses: Record<JobStatus, StatusLabel> = {
  RECEIVED: '접수',
  INSPECTING: '검사',
  PARSING: '파싱',
  DETECTING: '탐지',
  CLASSIFICATION_REVIEW: '분류 검토',
  MASKING: '마스킹',
  WAITING_APPROVAL: '승인대기',
  TRANSMITTING: '전송',
  POST_INSPECTING: '답변검사',
  COMPLETED: '완료',
  BLOCKED: '차단',
  FAILED: '실패',
  CANCELLED: '취소',
  UNKNOWN: '대기',
}

const stepIndex: Record<JobStatus, number> = {
  RECEIVED: 0,
  INSPECTING: 1,
  PARSING: 2,
  DETECTING: 3,
  CLASSIFICATION_REVIEW: 4,
  MASKING: 5,
  WAITING_APPROVAL: 6,
  TRANSMITTING: 7,
  POST_INSPECTING: 8,
  COMPLETED: 9,
  BLOCKED: 3,
  FAILED: 0,
  CANCELLED: 0,
  UNKNOWN: 0,
}

const detail: Record<JobStatus, string> = {
  RECEIVED: '분석 요청을 접수했습니다.',
  INSPECTING: '파일 안전성과 정책 적용 범위를 검사하는 중입니다.',
  PARSING: '문서 구조를 안전하게 파싱하는 중입니다.',
  DETECTING: '민감정보와 정책 위반 패턴을 탐지하는 중입니다.',
  CLASSIFICATION_REVIEW: '보안등급 추천이 완료되었습니다. 담당자의 최종 확정을 기다립니다.',
  MASKING: '민감정보 마스킹 처리를 준비하는 중입니다.',
  WAITING_APPROVAL: '담당자 승인을 기다리는 상태입니다.',
  TRANSMITTING: '정책에 맞는 payload 전송을 준비하는 중입니다.',
  POST_INSPECTING: '외부 AI 응답 검증을 준비하는 중입니다.',
  COMPLETED: '분석 작업이 완료되었습니다.',
  BLOCKED: '보안 정책에 의해 요청 처리가 차단되었습니다.',
  FAILED: '분석 작업에 실패했습니다.',
  CANCELLED: '분석 작업이 취소되었습니다.',
  UNKNOWN: '알 수 없는 처리 상태입니다. 상태를 다시 조회해 주세요.',
}

const gradeNames: Record<SecurityGrade, string> = {
  C: '기밀 · 외부 전송 차단',
  S: '민감 · 승인 후 전송',
  O: '공개 · 정책 검증 후 전송',
}

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

const terminalState = (
  status: JobStatus,
): 'completed' | 'failed' | 'blocked' | 'cancelled' | undefined =>
  status === 'COMPLETED'
    ? 'completed'
    : status === 'FAILED'
      ? 'failed'
      : status === 'BLOCKED'
        ? 'blocked'
        : status === 'CANCELLED'
          ? 'cancelled'
          : undefined

const normalizeStatus = (status: string): JobStatus =>
  status in statuses ? (status as JobStatus) : 'UNKNOWN'

const isGrade = (value: string | null | undefined): value is SecurityGrade =>
  value === 'C' || value === 'S' || value === 'O'

const isNotFound = (error: unknown) =>
  typeof error === 'object' && error !== null && (error as ApiError).status === 404

function Notice({ job, status }: { job: AnalysisJob; status: JobStatus }) {
  if (status === 'BLOCKED') return <Alert variant="danger" title="처리 차단">{detail.BLOCKED}</Alert>
  if (status === 'FAILED') return <Alert variant="danger" title="분석 실패">{job.failureMessage ?? detail.FAILED}</Alert>
  if (status === 'WAITING_APPROVAL') return <Alert variant="warning" title="승인 대기">{detail.WAITING_APPROVAL}</Alert>
  if (status === 'COMPLETED') return <Alert variant="success" title="분석 완료">{detail.COMPLETED}</Alert>
  if (status === 'CANCELLED') return <Alert variant="info" title="분석 취소">{detail.CANCELLED}</Alert>
  return <Alert variant="info" title="현재 처리 내용">{detail[status]}</Alert>
}

function ClassificationCard({ documentId, onConfirmed }: { documentId: number; onConfirmed?: (decision: ClassificationDecision) => void }) {
  const [recommendation, setRecommendation] = useState<ClassificationRecommendation | null>(null)
  const [decision, setDecision] = useState<ClassificationDecision | null>(null)
  const [selectedGrade, setSelectedGrade] = useState<SecurityGrade>('C')
  const [comment, setComment] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isConfirming, setIsConfirming] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError('')
    void Promise.all([
      getClassificationRecommendation(documentId),
      getClassificationDecision(documentId).catch((requestError: unknown) => {
        if (isNotFound(requestError)) return null
        throw requestError
      }),
    ])
      .then(([nextRecommendation, nextDecision]) => {
        if (cancelled) return
        setRecommendation(nextRecommendation)
        setDecision(nextDecision)
        if (isGrade(nextDecision?.confirmedGrade)) setSelectedGrade(nextDecision.confirmedGrade)
        else if (isGrade(nextRecommendation.recommendedGrade)) setSelectedGrade(nextRecommendation.recommendedGrade)
        if (nextDecision?.comment) setComment(nextDecision.comment)
      })
      .catch(() => {
        if (!cancelled) setError('분류 추천 결과를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [documentId])

  async function submitConfirmation() {
    setIsConfirming(true)
    setError('')
    try {
      const nextDecision = await confirmClassification(documentId, selectedGrade, comment)
      setDecision(nextDecision)
      onConfirmed?.(nextDecision)
    } catch {
      setError('등급 최종 확정에 실패했습니다. 권한과 서버 상태를 확인해 주세요.')
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <Card className="classification-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">AI CLASSIFICATION</p>
          <h2>보안등급 추천 및 최종 확정</h2>
        </div>
        {decision && <StatusBadge label="완료" />}
      </div>
      {isLoading && <p>분류 결과를 불러오는 중입니다.</p>}
      {error && <div className="section-gap"><Alert variant="danger" title="분류 처리 실패">{error}</Alert></div>}
      {!isLoading && recommendation && (
        <>
          <dl className="info-list">
            <div><dt>AI 추천</dt><dd>{recommendation.recommendedGrade ?? '판정 보류'}{recommendation.recommendedGrade && ` · ${gradeNames[recommendation.recommendedGrade as SecurityGrade]}`}</dd></div>
            <div><dt>신뢰도</dt><dd>{recommendation.confidence === null ? '-' : `${Math.round(recommendation.confidence * 100)}%`}</dd></div>
            <div><dt>추천 사유</dt><dd>{recommendation.reason}</dd></div>
            <div><dt>모델 버전</dt><dd><code>{recommendation.modelVersion}</code></dd></div>
          </dl>
          {decision ? (
            <div className="section-gap">
              <Alert variant="success" title={`최종 확정: ${decision.confirmedGrade}등급`}>
                {gradeNames[decision.confirmedGrade as SecurityGrade]} · 확정자 ID {decision.confirmedBy}
              </Alert>
            </div>
          ) : (
            <div className="section-gap">
              <label className="form-field">
                최종 확정 등급
                <select className="form-control" value={selectedGrade} onChange={(event) => setSelectedGrade(event.target.value as SecurityGrade)}>
                  <option value="C">C · 기밀 · 외부 전송 차단</option>
                  <option value="S">S · 민감 · 승인 후 전송</option>
                  <option value="O">O · 공개 · 정책 검증 후 전송</option>
                </select>
              </label>
              <label className="form-field section-gap">
                확정 의견(선택)
                <textarea className="form-control" rows={3} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="최종 확정 사유를 입력하세요." />
              </label>
              <div className="form-actions section-gap">
                <Button onClick={() => void submitConfirmation()} disabled={isConfirming}>
                  {isConfirming ? '확정 처리 중' : '등급 최종 확정'}
                </Button>
              </div>
            </div>
          )}
          <small>AI 추천은 참고자료이며, 최종 등급은 담당자 확정 결과를 사용합니다.</small>
        </>
      )}
    </Card>
  )
}

function GatewayCard({ documentId, refreshKey }: { documentId: number; refreshKey: number }) {
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4o-mini')
  const [prompt, setPrompt] = useState('이 문서를 간단히 요약해줘.')
  const [decision, setDecision] = useState<ClassificationDecision | null>(null)
  const [result, setResult] = useState<GatewayForwardResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError('')
    void getClassificationDecision(documentId)
      .then((nextDecision) => {
        if (!cancelled) setDecision(nextDecision)
      })
      .catch((requestError: unknown) => {
        if (isNotFound(requestError)) {
          if (!cancelled) setDecision(null)
          return
        }
        if (!cancelled) setError((requestError as ApiError).message ?? '최종 등급을 확인하지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [documentId, refreshKey])

  async function sendToGateway() {
    setIsSending(true)
    setError('')
    try {
      setResult(await forwardToGateway(documentId, { provider, model, prompt }))
    } catch (requestError: unknown) {
      setError((requestError as ApiError).message ?? 'Gateway 요청에 실패했습니다.')
    } finally {
      setIsSending(false)
    }
  }

  return (
    <Card className="gateway-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">LLM GATEWAY</p>
          <h2>정책 통과 문서 전송</h2>
        </div>
        {result && <StatusBadge label={result.status === 'COMPLETED' ? '완료' : result.status === 'BLOCKED' ? '차단' : result.status === 'WAITING_APPROVAL' ? '승인대기' : result.status === 'FAILED' ? '실패' : '전송'} />}
      </div>
      <p>확정된 보안등급과 전송 정책을 확인한 뒤 백엔드 Gateway를 통해 AI를 호출합니다.</p>
      {isLoading && <p>최종 등급을 확인하는 중입니다.</p>}
      {error && <div className="section-gap"><Alert variant="danger" title="Gateway 처리 실패">{error}</Alert></div>}
      {!isLoading && decision && (
        <>
          <dl className="info-list">
            <div><dt>확정 등급</dt><dd>{decision.confirmedGrade}</dd></div>
            <div><dt>전송 정책</dt><dd>{decision.confirmedGrade === 'C' ? '차단' : decision.confirmedGrade === 'S' ? '승인 필요' : '정책 검사 후 허용'}</dd></div>
          </dl>
          <div className="gateway-form section-gap">
            <label className="form-field">
              Provider
              <select className="form-control" value={provider} onChange={(event) => setProvider(event.target.value)}>
                <option value="openai">OpenAI</option>
              </select>
            </label>
            <label className="form-field">
              Model
              <input className="form-control" value={model} onChange={(event) => setModel(event.target.value)} />
            </label>
            <label className="form-field">
              요청 내용
              <textarea className="form-control" rows={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            </label>
            <div className="form-actions">
              <Button onClick={() => void sendToGateway()} disabled={isSending || !model.trim() || !prompt.trim()}>
                {isSending ? '정책 확인 및 전송 중' : 'Gateway 전송 테스트'}
              </Button>
            </div>
          </div>
        </>
      )}
      {!isLoading && !decision && !error && <Alert variant="warning" title="등급 확정 필요">먼저 C/S/O 최종 등급을 확정해야 Gateway를 호출할 수 있습니다.</Alert>}
      {result && (
        <div className="section-gap">
          {result.status === 'COMPLETED' && result.response ? (
            <Alert variant="success" title={`Gateway ${result.gatewayMode} · Post-Inspector ${result.postInspectionStatus ?? '-'}`}>
              <div className="gateway-result"><strong>정책 결과: {result.policyDecision}</strong><p>{result.response}</p></div>
            </Alert>
          ) : result.status === 'WAITING_APPROVAL' ? (
            <Alert variant="warning" title="S등급 승인 대기">
              승인 요청이 등록되었습니다. 승인자가 처리한 뒤에만 Gateway 전송이 진행됩니다.
              {result.approvalId && <div className="alert-action"><Link to="/approvals">승인 요청 화면으로 이동</Link> · Approval ID {result.approvalId}</div>}
            </Alert>
          ) : (
            <Alert variant="warning" title={`전송 결과: ${result.status}`}>
              정책 결과 `{result.policyDecision}` · Gateway `{result.gatewayMode}` · 확정 등급 `{result.confirmedGrade}`
            </Alert>
          )}
        </div>
      )}
    </Card>
  )
}

export function AnalysisPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { job, isLoading, networkError, notFound, refresh, setJob } = useJobPolling(jobId)
  const [showCancel, setShowCancel] = useState(false)
  const [isActing, setIsActing] = useState(false)
  const [toast, setToast] = useState('')
  const [classificationVersion, setClassificationVersion] = useState(0)

  async function copyJobId() {
    if (!job?.jobId) return
    try {
      await navigator.clipboard.writeText(job.jobId)
      setToast('Job ID가 복사되었습니다.')
    } catch {
      setToast('Job ID 복사에 실패했습니다. 직접 선택해 복사해 주세요.')
    }
  }

  async function confirmCancel() {
    if (!job) return
    setIsActing(true)
    try {
      setJob(await cancelJob(job.jobId))
      setShowCancel(false)
    } catch {
      setToast('분석 취소 요청을 처리하지 못했습니다. 다시 시도해 주세요.')
    } finally {
      setIsActing(false)
    }
  }

  async function retry() {
    if (!job) return
    setIsActing(true)
    try {
      const result = await retryJob(job.jobId)
      setJob(result.job)
      if (result.job.jobId !== job.jobId) navigate(`/analysis/${result.job.jobId}`, { replace: true })
    } catch {
      setToast('재시도 요청을 처리하지 못했습니다. 다시 시도해 주세요.')
    } finally {
      setIsActing(false)
    }
  }

  if (isLoading && !job) return <LoadingState label="분석 작업 상태를 불러오는 중입니다." />
  if (notFound) return <section><h1>분석 작업을 찾을 수 없습니다.</h1><ErrorState label="입력한 Job ID에 해당하는 분석 작업이 없습니다." /><Button variant="secondary" onClick={() => navigate('/upload')}>문서 업로드로 이동</Button></section>
  if (!job) return <section><h1>분석 상태를 확인할 수 없습니다.</h1><ErrorState label="Job 정보를 불러오지 못했습니다." /><Button onClick={() => void refresh()}>다시 조회</Button></section>

  const status = normalizeStatus(job.status)
  const terminal = isTerminalJob(job)
  const classificationReady = [
    'CLASSIFICATION_REVIEW',
    'MASKING',
    'WAITING_APPROVAL',
    'TRANSMITTING',
    'POST_INSPECTING',
    'COMPLETED',
  ].includes(status)
  return (
    <section aria-live="polite">
      <p className="eyebrow">ASYNC ANALYSIS JOB</p>
      <div className="page-title-row">
        <div><h1>문서 분석</h1><p>Job ID를 기준으로 현재 처리 상태를 다시 조회합니다.</p></div>
        <StatusBadge label={statuses[status]} />
      </div>
      {networkError && <div className="section-gap"><Alert variant="warning" title="상태 조회 지연">{networkError}<div className="alert-action"><Button size="sm" variant="secondary" onClick={() => void refresh()}>다시 조회</Button></div></Alert></div>}
      <div className="analysis-grid">
        <Card><div className="job-id-row"><div><p className="eyebrow">JOB ID</p><code>{job.jobId}</code></div><Button size="sm" variant="ghost" onClick={() => void copyJobId()}>복사</Button></div><dl className="info-list"><div><dt>파일</dt><dd>{job.file.fileName}</dd></div><div><dt>현재 상태</dt><dd><StatusBadge label={statuses[status]} /></dd></div><div><dt>생성 시각</dt><dd>{formatDate(job.createdAt)}</dd></div><div><dt>마지막 업데이트</dt><dd>{formatDate(job.updatedAt)}</dd></div></dl></Card>
        <Card><p className="eyebrow">PROGRESS</p><div className="progress-value">{job.progress}%</div><div className="progress-bar" role="progressbar" aria-label="분석 진행률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={job.progress}><span style={{ width: `${job.progress}%` }} /></div><p>{terminal ? '처리가 종료되었습니다.' : `${job.currentStep} 단계를 처리 중입니다.`}</p></Card>
      </div>
      <Card className="analysis-step-card"><h2>분석 단계</h2><Stepper activeStep={stepIndex[status]} terminalState={terminalState(status)} /></Card>
      {job.documentId && classificationReady && <ClassificationCard documentId={job.documentId} onConfirmed={() => setClassificationVersion((current) => current + 1)} />}
      {job.documentId && classificationReady && <GatewayCard documentId={job.documentId} refreshKey={classificationVersion} />}
      <div className="section-gap"><Notice job={job} status={status} /></div>
      <div className="job-actions">{job.canCancel && <Button variant="danger" onClick={() => setShowCancel(true)}>분석 취소</Button>}{status === 'FAILED' && <Button onClick={() => void retry()} disabled={isActing}>다시 시도</Button>}{(status === 'COMPLETED' || status === 'BLOCKED') && job.requestId && <Button variant="secondary" onClick={() => navigate(`/result/${job.requestId}`)}>결과 확인</Button>}</div>
      {showCancel && <ConfirmDialog title="분석 작업 취소" message="현재 분석 작업을 취소하시겠습니까? 취소된 작업은 자동으로 다시 시작되지 않습니다." confirmLabel="분석 취소" isConfirming={isActing} onClose={() => setShowCancel(false)} onConfirm={() => void confirmCancel()} />}
      {toast && <div className="toast-anchor"><Toast message={toast} /></div>}
    </section>
  )
}
