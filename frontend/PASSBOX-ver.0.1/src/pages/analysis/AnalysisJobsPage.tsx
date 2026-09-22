import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRecentJobs } from '../../api/jobs'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { EmptyState, LoadingState } from '../../components/common/StateViews'
import { StatusBadge, type StatusLabel } from '../../components/common/StatusBadge'
import type { AnalysisJob, JobStatus } from '../../types/security'

const terminalStatuses = new Set<JobStatus>(['COMPLETED', 'BLOCKED', 'FAILED', 'CANCELLED'])
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

export function AnalysisJobsPage() {
  const [jobs, setJobs] = useState<AnalysisJobRow[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadJobs = useCallback(async () => {
    try {
      setError('')
      const nextJobs = await getRecentJobs()
      setJobs(nextJobs.map((job) => ({ ...job, id: job.jobId })))
    } catch {
      setError('문서 분석 작업 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadJobs()
    const timer = window.setInterval(() => void loadJobs(), 5_000)
    return () => window.clearInterval(timer)
  }, [loadJobs])

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
    { key: 'action', header: '상세', render: (job) => <Link to={`/analysis/${job.jobId}`} className="table-link">상세 보기</Link> },
  ]

  if (isLoading) return <LoadingState label="문서 분석 작업을 불러오는 중입니다." />

  return (
    <section>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">문서 분석 작업</p>
          <h1>문서 분석 작업</h1>
          <p>분석을 시작한 문서의 진행 상태와 결과를 한 곳에서 확인합니다.</p>
        </div>
        <Button variant="secondary" onClick={() => void loadJobs()}>새로고침</Button>
      </div>
      {error && <div className="section-gap"><Alert variant="danger" title="목록 조회 실패">{error}</Alert></div>}
      {jobs.length === 0 ? (
        <Card>
          <EmptyState label="아직 시작한 문서 분석 작업이 없습니다. 문서를 업로드하고 분석을 시작해 주세요." />
          <div className="form-actions"><Link to="/upload" className="button button--primary">문서 업로드</Link></div>
        </Card>
      ) : (
        <>
          <div className="analysis-list-summary">
            <strong>최근 분석 작업 {jobs.length}건</strong>
            <span>{jobs.some((job) => !terminalStatuses.has(job.status)) ? '진행 중인 작업은 자동으로 갱신됩니다.' : '모든 작업이 현재 상태로 반영되었습니다.'}</span>
          </div>
          <DataTable columns={columns} rows={jobs} />
        </>
      )}
    </section>
  )
}
