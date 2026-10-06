import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { Link } from 'react-router-dom'
import analysisDetailExample from '../../assets/onboarding-analysis-detail-example.png'
import analysisProgressExample from '../../assets/onboarding-analysis-progress-example.png'
import { getRecentJobs } from '../../api/jobs'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState, LoadingState } from '../../components/common/StateViews'
import { StatusBadge, type StatusLabel } from '../../components/common/StatusBadge'
import type { AnalysisJob, JobStatus } from '../../types/security'
import { paginate } from '../../utils/paginate'

const terminalStatuses = new Set<JobStatus>(['COMPLETED', 'BLOCKED', 'FAILED', 'CANCELLED'])
const JOBS_PAGE_SIZE = 10
type AnalysisJobRow = AnalysisJob & { id: string }
const statusLabels: Record<JobStatus, StatusLabel> = {
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

const formatDate = (value: string) => new Intl.DateTimeFormat('ko-KR', {
  dateStyle: 'short',
  timeStyle: 'short',
}).format(new Date(value))

const analysisDetailTourStorageKey = 'passbox:onboarding:analysis-list-detail:v1'
const JOBS_PAGE_STORAGE_KEY = 'passbox:analysis-jobs:page'

const shouldShowDetailTour = () => {
  try {
    return window.localStorage.getItem(analysisDetailTourStorageKey) !== 'completed'
  } catch {
    return true
  }
}

// 작업 상세로 들어갔다가 돌아왔을 때 보던 페이지가 1페이지로 초기화되지 않도록
// 세션 스토리지에 마지막 페이지를 기억해 둔다. 새 창/다른 탭에는 영향 없음.
function readStoredPage(): number {
  try {
    const raw = window.sessionStorage.getItem(JOBS_PAGE_STORAGE_KEY)
    const parsed = raw ? Number.parseInt(raw, 10) : 1
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
  } catch {
    return 1
  }
}

function storePage(page: number) {
  try {
    window.sessionStorage.setItem(JOBS_PAGE_STORAGE_KEY, String(page))
  } catch {
    // 세션 스토리지를 쓸 수 없는 환경이면 페이지 기억만 건너뛴다.
  }
}

export function AnalysisJobsPage() {
  const [jobs, setJobs] = useState<AnalysisJobRow[]>([])
  const [page, setPageState] = useState(() => readStoredPage())
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const previousQuery = useRef(searchQuery)

  function setPage(next: number) {
    setPageState(next)
    storePage(next)
  }

  function handleSearchChange(event: ChangeEvent<HTMLInputElement>) {
    setSearchInput(event.target.value)
  }
  const [analysisTourStep, setAnalysisTourStep] = useState<0 | 1 | 2 | null>(() => (shouldShowDetailTour() ? 0 : null))
  const [isTourTransitioning, setIsTourTransitioning] = useState(false)
  const tourTransitionTimer = useRef<number | null>(null)

  function restartAnalysisListOnboarding() {
    if (tourTransitionTimer.current !== null) window.clearTimeout(tourTransitionTimer.current)
    setIsTourTransitioning(false)
    setAnalysisTourStep(0)
  }

  function completeAnalysisListOnboarding() {
    if (tourTransitionTimer.current !== null) window.clearTimeout(tourTransitionTimer.current)
    tourTransitionTimer.current = null
    try {
      window.localStorage.setItem(analysisDetailTourStorageKey, 'completed')
    } catch {
      // Completing the visible guide still works when storage is restricted.
    }
    setIsTourTransitioning(false)
    setAnalysisTourStep(null)
  }

  function advanceAnalysisListOnboarding() {
    if (analysisTourStep === null || isTourTransitioning) return
    setIsTourTransitioning(true)
    tourTransitionTimer.current = window.setTimeout(() => {
      tourTransitionTimer.current = null
      if (analysisTourStep === 2) {
        completeAnalysisListOnboarding()
        return
      }
      setAnalysisTourStep((current) => (current === null ? null : current + 1) as 0 | 1 | 2)
      setIsTourTransitioning(false)
    }, 160)
  }

  const loadJobs = useCallback(async () => {
    try {
      setError('')
      const nextJobs = await getRecentJobs(100, searchQuery)
      setJobs(nextJobs.map((job) => ({ ...job, id: job.jobId })))
    } catch {
      setError('문서 분석 작업 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery])

  useEffect(() => {
    void loadJobs()
    const timer = window.setInterval(() => void loadJobs(), 5_000)
    return () => window.clearInterval(timer)
  }, [loadJobs])

  // 입력 후 300ms 동안 추가 입력이 없으면 실제 조회 조건에 반영한다(타자마다 요청하지 않도록).
  useEffect(() => {
    const timer = window.setTimeout(() => setSearchQuery(searchInput.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  // 검색 조건이 실제로 바뀐 경우에만 1페이지로 되돌린다 — 세션에 저장된 페이지를
  // 마운트 시점에 복원하는 것까지 덮어쓰지 않기 위해 이전 값과 비교한다.
  useEffect(() => {
    if (previousQuery.current !== searchQuery) {
      previousQuery.current = searchQuery
      setPage(1)
    }
  }, [searchQuery])

  useEffect(() => () => {
    if (tourTransitionTimer.current !== null) window.clearTimeout(tourTransitionTimer.current)
  }, [])

  const columns: DataTableColumn<AnalysisJobRow>[] = [
    {
      key: 'file',
      header: '문서',
      render: (job) => <Link to={`/analysis/${job.jobId}`} className="table-link">{job.file.fileName}</Link>,
    },
    { key: 'job', header: '작업 ID', render: (job) => <code>{job.jobId}</code> },
    { key: 'status', header: '현재 상태', render: (job) => <StatusBadge label={statusLabels[job.status] ?? statusLabels.UNKNOWN} /> },
    { key: 'progress', header: '진행률', render: (job) => `${job.progress}% · ${job.currentStep}` },
    { key: 'created', header: '시작 시각', render: (job) => formatDate(job.createdAt) },
    { key: 'action', header: '상세', render: (job) => <Link to={`/analysis/${job.jobId}`} className={`table-link ${analysisTourStep === 0 && job.id === jobs[0]?.id ? 'analysis-detail-tour__target' : ''}`.trim()}>상세 보기</Link> },
  ]

  if (isLoading) return <LoadingState label="문서 분석 작업을 불러오는 중입니다." />

  const jobsPage = paginate(jobs, page, JOBS_PAGE_SIZE)

  return (
    <section>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">문서 분석 작업</p>
          <h1>문서 분석 작업</h1>
          <p>분석을 시작한 문서의 진행 상태와 결과를 한 곳에서 확인합니다.</p>
        </div>
        <div className="table-actions">
          <Button size="sm" variant="ghost" onClick={restartAnalysisListOnboarding}>사용 안내 다시 보기</Button>
          <Button variant="secondary" onClick={() => void loadJobs()}>새로고침</Button>
        </div>
      </div>
      <label className="form-field analysis-search section-gap">
        문서 검색
        <input
          type="search"
          className="form-control"
          value={searchInput}
          onChange={handleSearchChange}
          placeholder="파일명 또는 문서 내용으로 이전 작업을 검색하세요."
        />
      </label>
      {error && <div className="section-gap"><Alert variant="danger" title="목록 조회 실패">{error}</Alert></div>}
      {analysisTourStep === 0 && (
        <Card className={`analysis-detail-tour__example ${isTourTransitioning ? 'onboarding-panel--leaving' : ''}`.trim()}>
          <div className="analysis-detail-tour__example-frame">
            <img src={analysisDetailExample} alt="문서 분석 작업 목록의 상세 보기 버튼 예시" />
            <span className="analysis-detail-tour__image-focus" aria-hidden="true" />
          </div>
          <p>온보딩 예시 · 실제 파일이 추가되거나 저장되지는 않습니다.</p>
        </Card>
      )}
      {analysisTourStep === 0 && (
        <aside className={`analysis-detail-tour ${isTourTransitioning ? 'onboarding-panel--leaving' : ''}`.trim()} aria-label="문서 분석 작업 안내 1단계">
          <p>시작 안내 · 1 / 3</p>
          <h2>상세 보기로 분석 화면을 여세요</h2>
          <span>선택한 문서의 상세 보기를 누르면 진행률, 현재 상태와 분석 단계를 확인할 수 있습니다.</span>
          <Button size="sm" onClick={advanceAnalysisListOnboarding}>다음 안내</Button>
        </aside>
      )}
      {(analysisTourStep === 1 || analysisTourStep === 2) && (
        <div key={analysisTourStep} className={`analysis-list-onboarding-stage ${isTourTransitioning ? 'onboarding-panel--leaving' : ''}`.trim()}>
          <Card className="analysis-progress-tour__example">
            <div className="analysis-progress-tour__example-frame">
              <img src={analysisProgressExample} alt="진행률과 분석 단계가 표시된 문서 분석 화면 예시" />
              {analysisTourStep === 1 && <span className="analysis-progress-tour__image-focus analysis-progress-tour__image-focus--progress" aria-hidden="true" />}
              {analysisTourStep === 2 && <span className="analysis-progress-tour__image-focus analysis-progress-tour__image-focus--steps" aria-hidden="true" />}
            </div>
            <p>온보딩 예시 · 실제 분석 정보가 추가되거나 저장되지는 않습니다.</p>
          </Card>
          <aside className="analysis-detail-tour" aria-live="polite" aria-label="문서 분석 진행 안내 2단계">
            <p>시작 안내 · {analysisTourStep === 1 ? '2 / 3' : '3 / 3'}</p>
            <h2>{analysisTourStep === 1 ? '진행률을 확인하세요' : '분석 단계를 확인하세요'}</h2>
            <span>{analysisTourStep === 1 ? '진행률은 작업이 어느 정도 처리되었는지 보여 줍니다. 숫자와 막대, 현재 처리 중인 단계 이름을 함께 확인하세요.' : '분석 단계는 접수부터 검사·파싱·탐지·마스킹을 거쳐 완료까지 순서대로 갱신됩니다. 완료·진행 중·대기 상태를 한눈에 확인할 수 있습니다.'}</span>
            <Button size="sm" onClick={advanceAnalysisListOnboarding}>{analysisTourStep === 1 ? '다음 안내' : '완료'}</Button>
          </aside>
        </div>
      )}
      {jobs.length === 0 ? (
        <Card>
          {searchQuery ? (
            <EmptyState label={`'${searchQuery}'와 일치하는 작업이 없습니다. 파일명이나 문서 내용을 다시 확인해 주세요.`} />
          ) : (
            <>
              <EmptyState label="아직 시작한 문서 분석 작업이 없습니다. 문서를 업로드하고 분석을 시작해 주세요." />
              <div className="form-actions"><Link to="/upload" className="button button--primary">문서 업로드</Link></div>
            </>
          )}
        </Card>
      ) : (
        <>
          <div className="analysis-list-summary">
            <strong>{searchQuery ? `'${searchQuery}' 검색 결과 ${jobs.length}건` : `최근 분석 작업 ${jobs.length}건`}</strong>
            <span>{jobs.some((job) => !terminalStatuses.has(job.status)) ? '진행 중인 작업은 자동으로 갱신됩니다.' : '모든 작업이 현재 상태로 반영되었습니다.'}</span>
          </div>
          <DataTable columns={columns} rows={jobsPage.pageItems} />
          <Pagination page={jobsPage.safePage} pageCount={jobsPage.pageCount} pageSize={JOBS_PAGE_SIZE} totalCount={jobs.length} onPageChange={setPage} />
        </>
      )}
    </section>
  )
}
