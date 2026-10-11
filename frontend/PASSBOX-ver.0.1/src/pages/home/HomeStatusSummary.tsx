import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPendingApprovals } from '../../api/approvals'
import { getRecentJobs } from '../../api/jobs'
import { getPendingReviewRequests } from '../../api/reviewRequests'
import { useAuth } from '../../hooks/useAuth'
import { usePermission } from '../../hooks/usePermission'
import type { AnalysisJob, JobStatus } from '../../types/security'

const IN_PROGRESS: JobStatus[] = ['RECEIVED', 'INSPECTING', 'PARSING', 'DETECTING', 'MASKING', 'TRANSMITTING', 'POST_INSPECTING']
const NEEDS_REVIEW: JobStatus[] = ['CLASSIFICATION_REVIEW', 'WAITING_APPROVAL']

const STATUS_LABEL: Partial<Record<JobStatus, string>> = {
  COMPLETED: '처리 완료',
  BLOCKED: '전송 차단',
  FAILED: '처리 실패',
  CANCELLED: '취소됨',
  CLASSIFICATION_REVIEW: '등급 검토 대기',
  WAITING_APPROVAL: '승인 대기',
}

type JobState = { kind: 'loading' } | { kind: 'error' } | { kind: 'ready'; jobs: AnalysisJob[] }
type QueueState = { kind: 'loading' | 'error' | 'skipped' } | { kind: 'ready'; pending: number; escalated: number }

export function HomeStatusSummary() {
  const navigate = useNavigate()
  const { session } = useAuth()
  // The jobs API returns only the caller's own jobs for USER, the whole tenant otherwise.
  const title = session?.role === 'USER' ? '내 처리 현황' : '기관 처리 현황'
  const [state, setState] = useState<JobState>({ kind: 'loading' })

  // 역할별 "내가 처리할 일" — 승인(APPROVER류)과 C등급 재검토(OPERATOR류)는 서로 다른 권한이라
  // 각각 실제 대기열 API로 따로 확인한다. 에스컬레이션은 지연 표시용으로 만든 임의 기준이 아니라
  // 서버의 SLA(기본 4시간, app/escalation.py)를 그대로 따른다.
  const canApprove = usePermission(['APPROVER', 'SECURITY_ADMIN', 'ADMIN'])
  const canReview = usePermission(['OPERATOR', 'SECURITY_ADMIN', 'ADMIN'])
  const [approvalQueue, setApprovalQueue] = useState<QueueState>({ kind: canApprove ? 'loading' : 'skipped' })
  const [reviewQueue, setReviewQueue] = useState<QueueState>({ kind: canReview ? 'loading' : 'skipped' })

  useEffect(() => {
    let cancelled = false
    getRecentJobs(100)
      .then((jobs) => { if (!cancelled) setState({ kind: 'ready', jobs }) })
      .catch(() => { if (!cancelled) setState({ kind: 'error' }) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!canApprove) return
    let cancelled = false
    getPendingApprovals()
      .then((items) => { if (!cancelled) setApprovalQueue({ kind: 'ready', pending: items.length, escalated: items.filter((i) => i.isEscalated).length }) })
      .catch(() => { if (!cancelled) setApprovalQueue({ kind: 'error' }) })
    return () => { cancelled = true }
  }, [canApprove])

  useEffect(() => {
    if (!canReview) return
    let cancelled = false
    getPendingReviewRequests()
      .then((items) => { if (!cancelled) setReviewQueue({ kind: 'ready', pending: items.length, escalated: items.filter((i) => i.isEscalated).length }) })
      .catch(() => { if (!cancelled) setReviewQueue({ kind: 'error' }) })
    return () => { cancelled = true }
  }, [canReview])

  const actionItems = [
    canApprove && approvalQueue.kind === 'ready'
      ? { label: '내 승인 대기함', value: `${approvalQueue.pending}건`, sub: approvalQueue.escalated ? `4시간 이상 지연 ${approvalQueue.escalated}건` : approvalQueue.pending ? '마스킹 내용을 확인하고 승인하세요' : '대기 중인 요청 없음', warn: approvalQueue.escalated > 0, path: '/approvals' }
      : null,
    canReview && reviewQueue.kind === 'ready'
      ? { label: 'C등급 재검토 요청', value: `${reviewQueue.pending}건`, sub: reviewQueue.escalated ? `4시간 이상 지연 ${reviewQueue.escalated}건` : reviewQueue.pending ? '전송 차단 판정에 대한 이의 제기' : '대기 중인 요청 없음', warn: reviewQueue.escalated > 0, path: '/reviews' }
      : null,
  ].filter((item): item is { label: string; value: string; sub: string; warn: boolean; path: string } => item !== null)

  const actionSection = actionItems.length > 0 && (
    <section className="home-status home-status--actions" aria-labelledby="home-actions-title">
      <div className="home-status__head">
        <h2 id="home-actions-title">내가 처리할 일</h2>
      </div>
      <div className="home-status__grid">
        {actionItems.map((item) => (
          <button key={item.label} type="button" className={`home-status__card${item.warn ? ' is-warn' : ''}`} onClick={() => navigate(item.path)}>
            <small>{item.label}</small>
            <strong>{item.value}</strong>
            <span>{item.sub}</span>
          </button>
        ))}
      </div>
    </section>
  )

  if (state.kind === 'loading') {
    return <>{actionSection}<section className="home-status" aria-busy="true" aria-label={title}><p className="home-status__note">처리 현황을 불러오는 중입니다…</p></section></>
  }
  if (state.kind === 'error') {
    return <>{actionSection}<section className="home-status" aria-label={title}><p className="home-status__note">처리 현황을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p></section></>
  }

  const { jobs } = state
  if (jobs.length === 0) {
    return (
      <>
        {actionSection}
        <section className="home-status home-status--empty" aria-label={title}>
          <p className="home-status__note">아직 분석한 문서가 없습니다. 첫 문서를 업로드해 보안 검사를 시작해 보세요.</p>
          <button type="button" className="home-status__cta" onClick={() => navigate('/upload')}>문서 업로드</button>
        </section>
      </>
    )
  }

  const inProgress = jobs.filter((job) => IN_PROGRESS.includes(job.status)).length
  const waiting = jobs.filter((job) => NEEDS_REVIEW.includes(job.status))
  const blocked = jobs.filter((job) => job.status === 'BLOCKED').length
  const latest = jobs[0]
  const oldestWaitDays = waiting.length
    ? Math.floor((Date.now() - Math.min(...waiting.map((job) => new Date(job.createdAt).getTime()))) / 86_400_000)
    : 0

  const cards = [
    { label: '진행 중인 분석', value: `${inProgress}건`, sub: inProgress ? '분석이 끝나면 결과를 확인하세요' : '지금 처리 중인 문서 없음', path: '/analysis/recent' },
    {
      // 여기 표시되는 대기일수는 참고용 현황이며, 실제 지연 기준(SLA)은 위 "내가 처리할 일"의
      // 승인·재검토 대기함이 서버 기준(4시간)으로 따로 알려준다.
      label: '검토·승인 대기',
      value: `${waiting.length}건`,
      sub: waiting.length ? (oldestWaitDays > 0 ? `가장 오래된 건 ${oldestWaitDays}일째 대기` : '오늘 접수된 건만 대기 중') : '대기 중인 건 없음',
      path: '/analysis/recent',
    },
    { label: '전송 차단', value: `${blocked}건`, sub: blocked ? '보안 담당자 확인이 필요합니다' : '차단된 건 없음', warn: blocked > 0, path: '/analysis/recent' },
    {
      label: '가장 최근 문서',
      value: latest.file.fileName,
      sub: STATUS_LABEL[latest.status] ?? latest.currentStep,
      path: `/analysis/${latest.jobId}`,
    },
  ]

  return (
    <>
      {actionSection}
      <section className="home-status" aria-labelledby="home-status-title">
        <div className="home-status__head">
          <h2 id="home-status-title">{title}</h2>
          <span>최근 {jobs.length}건 기준</span>
        </div>
        <div className="home-status__grid">
          {cards.map((card) => (
            <button key={card.label} type="button" className={`home-status__card${'warn' in card && card.warn ? ' is-warn' : ''}`} onClick={() => navigate(card.path)}>
              <small>{card.label}</small>
              <strong title={card.value}>{card.value}</strong>
              {card.sub && <span>{card.sub}</span>}
            </button>
          ))}
        </div>
      </section>
    </>
  )
}
