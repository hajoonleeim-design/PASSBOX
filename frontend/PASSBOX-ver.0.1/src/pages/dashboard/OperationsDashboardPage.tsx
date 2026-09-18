// 운영 지표와 알림을 역할별로 보여 주는 관리자 대시보드 화면입니다.
import { useParams } from 'react-router-dom'
import { Alert } from '../../components/common/Alert'
import { Badge, type BadgeVariant } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { GradeBadge } from '../../components/security/GradeBadge'
import { useAuth } from '../../hooks/useAuth'
import { useOperations } from '../../hooks/useOperations'
import type { OperationsIncident, ProviderHealth, ProviderStatus, RecentOperationsJob } from '../../types/operations'

const providerVariant: Record<ProviderHealth, BadgeVariant> = { HEALTHY: 'success', DEGRADED: 'warning', DOWN: 'danger', UNKNOWN: 'neutral' }
const providerLabel: Record<ProviderHealth, string> = { HEALTHY: '정상', DEGRADED: '지연', DOWN: '장애', UNKNOWN: '확인 불가' }
const incidentVariant: Record<OperationsIncident['severity'], BadgeVariant> = { LOW: 'info', MEDIUM: 'warning', HIGH: 'danger', CRITICAL: 'danger' }
const formatDate = (value: string) => new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))
const formatDuration = (milliseconds: number | undefined) => milliseconds === undefined ? 'N/A' : `${(milliseconds / 1000).toFixed(1)}초`

function StatusPill({ status }: { status: string }) {
  const variant: BadgeVariant = ['COMPLETED', 'ALLOWED'].includes(status) ? 'success' : ['BLOCKED', 'FAILED', 'DOWN'].includes(status) ? 'danger' : ['WAITING_APPROVAL', 'DEGRADED'].includes(status) ? 'warning' : 'info'
  const labels: Record<string, string> = { DETECTING: '탐지 중', COMPLETED: '완료', BLOCKED: '차단', WAITING_APPROVAL: '승인 대기', FAILED: '실패' }
  return <Badge variant={variant}><span aria-hidden="true">●</span> {labels[status] ?? status}</Badge>
}

const providerColumns: DataTableColumn<ProviderStatus>[] = [
  { key: 'name', header: 'Provider', render: (row) => row.providerName },
  { key: 'status', header: '상태', render: (row) => <Badge variant={providerVariant[row.status]}><span aria-hidden="true">●</span> {row.status} · {providerLabel[row.status]}</Badge> },
  { key: 'response', header: '응답 시간', render: (row) => row.responseTimeMs === undefined ? 'N/A' : `${row.responseTimeMs.toLocaleString()} ms` },
  { key: 'checked', header: '마지막 확인', render: (row) => formatDate(row.lastCheckedAt) },
  { key: 'message', header: '메시지', render: (row) => row.message },
]

const jobColumns: DataTableColumn<RecentOperationsJob>[] = [
  { key: 'job', header: 'Job ID', render: (row) => <code>{row.jobId}</code> },
  { key: 'request', header: 'Request ID', render: (row) => <code>{row.requestId}</code> },
  { key: 'file', header: '파일명', render: (row) => row.fileNameDisplay },
  { key: 'status', header: '상태', render: (row) => <StatusPill status={row.status} /> },
  { key: 'step', header: '현재 단계', render: (row) => row.currentStep },
  { key: 'grade', header: 'C/S/O', render: (row) => <GradeBadge grade={row.grade} /> },
  { key: 'started', header: '시작 시간', render: (row) => formatDate(row.startedAt) },
  { key: 'duration', header: '처리 시간', render: (row) => formatDuration(row.processingTimeMs) },
]

export function OperationsDashboardPage() {
  const { scenario = 'mock-normal' } = useParams()
  const { session } = useAuth()
  const { dashboard, isLoading, errorCode, refresh } = useOperations(scenario, session?.role)

  if (isLoading && !dashboard) return <LoadingState label="운영 데이터를 불러오는 중입니다." />
  if (errorCode === 'FORBIDDEN') return <section><h1>운영 대시보드 권한이 없습니다.</h1><ErrorState label="관리자만 운영 현황을 조회할 수 있습니다." /></section>
  if (errorCode === 'NOT_FOUND') return <section><h1>대시보드 시나리오를 찾을 수 없습니다.</h1><ErrorState label="요청한 운영 데이터 시나리오가 없습니다." /></section>
  if (errorCode || !dashboard) return <section><h1>운영 데이터를 불러오지 못했습니다.</h1><ErrorState label="네트워크 연결을 확인한 뒤 다시 시도해 주세요." /><Button onClick={() => void refresh()}>다시 조회</Button></section>

  const summary = [
    ['전체 요청', dashboard.summary.totalRequests, '현재 집계 기준 요청'],
    ['처리 완료', dashboard.summary.completedRequests, `성공률 ${dashboard.summary.successRate}%`],
    ['처리 중', dashboard.summary.processingRequests, `대기열 ${dashboard.queue.totalQueued}건`],
    ['차단', dashboard.summary.blockedRequests, '보안 정책 차단'],
    ['실패', dashboard.summary.failedRequests, `실패율 ${dashboard.summary.failureRate}%`],
  ]
  const queueItems = [['접수', dashboard.queue.received], ['검사', dashboard.queue.inspecting], ['파싱', dashboard.queue.parsing], ['탐지', dashboard.queue.detecting], ['마스킹', dashboard.queue.masking], ['승인대기', dashboard.queue.waitingApproval], ['전송', dashboard.queue.transmitting], ['답변검사', dashboard.queue.postInspecting]]
  const csoTotal = dashboard.csoDistribution.reduce((total, item) => total + item.count, 0)

  return <section className="operations-dashboard">
    <div className="page-title-row"><div><p className="eyebrow">OPERATIONS OVERVIEW</p><h1>운영 대시보드</h1><p>데이터 기준 시각: {formatDate(dashboard.generatedAt)}</p></div><Button onClick={() => void refresh()} disabled={isLoading}>{isLoading ? '새로고침 중' : '새로고침'}</Button></div>

    <div className="operations-summary-grid">{summary.map(([label, value, description]) => <Card key={label} className="operations-kpi"><span>{label}</span><strong>{Number(value).toLocaleString()}</strong><small>{description}</small></Card>)}</div>

    <div className="operations-layout">
      <Card><div className="section-heading"><div><h2>Queue 현황</h2><p>현재 대기열: {dashboard.queue.totalQueued.toLocaleString()}건</p></div></div><div className="queue-grid">{queueItems.map(([label, count]) => <div className="queue-item" key={label}><span>{label}</span><strong>{Number(count).toLocaleString()}건</strong></div>)}</div></Card>
      <Card><h2>처리 성능</h2><div className="performance-list"><div><span>시간당 처리량</span><strong>{dashboard.performance.throughputPerHour.toLocaleString()}건</strong></div><div><span>평균 처리시간</span><strong>{formatDuration(dashboard.performance.averageProcessingTimeMs)}</strong></div><div><span>P95 처리시간</span><strong>{formatDuration(dashboard.performance.p95ProcessingTimeMs)}</strong></div><div><span>성공률</span><strong>{dashboard.summary.successRate}%</strong><div className="metric-bar" role="progressbar" aria-label="성공률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={dashboard.summary.successRate}><span style={{ width: `${dashboard.summary.successRate}%` }} /></div></div><div><span>실패율</span><strong>{dashboard.summary.failureRate}%</strong><div className="metric-bar metric-bar--danger" role="progressbar" aria-label="실패율" aria-valuemin={0} aria-valuemax={100} aria-valuenow={dashboard.summary.failureRate}><span style={{ width: `${dashboard.summary.failureRate}%` }} /></div></div></div></Card>
    </div>

    <Card className="operations-section"><h2>AI Provider 상태</h2><DataTable columns={providerColumns} rows={dashboard.providers.map((item) => ({ ...item, id: item.providerId }))} /></Card>
    <Card className="operations-section"><h2>최근 Job</h2><DataTable columns={jobColumns} rows={dashboard.recentJobs.map((item) => ({ ...item, id: item.jobId }))} emptyMessage="현재 표시할 최근 Job이 없습니다." /></Card>

    <div className="operations-layout">
      <Card><h2>C/S/O 분포</h2><div className="distribution-list">{dashboard.csoDistribution.map((item) => <div key={item.grade}><GradeBadge grade={item.grade} /><strong>{item.count.toLocaleString()}건</strong><span>{csoTotal === 0 ? 0 : ((item.count / csoTotal) * 100).toFixed(1)}%</span></div>)}</div></Card>
      <Card><h2>Incident / 장애 현황</h2>{dashboard.incidents.length === 0 ? <EmptyState label="현재 열린 Incident가 없습니다." /> : <div className="incident-list">{dashboard.incidents.map((item) => <div key={item.incidentId} className="incident-item"><div><Badge variant={incidentVariant[item.severity]}><span aria-hidden="true">●</span> {item.severity} · {item.status}</Badge><strong>{item.incidentId}</strong></div><p>{item.summary}</p><small>발생: {formatDate(item.occurredAt)}{item.relatedJobId ? ` · 관련 Job: ${item.relatedJobId}` : ''}</small></div>)}</div>}</Card>
    </div>
    {dashboard.providers.some((item) => item.status === 'DOWN') && <div className="section-gap"><Alert variant="danger" title="Provider 장애 감지">Provider 상태를 확인할 수 없습니다. 이 화면은 현황 조회 전용이며 실제 장애 조치는 운영 절차에 따라 수행해야 합니다.</Alert></div>}
  </section>
}
