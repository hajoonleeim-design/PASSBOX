import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useOperations } from '../../hooks/useOperations'
import type { RecentOperationsJob } from '../../types/operations'
import '../../styles/stripe-radar.css'

const RULES = [
  { name: 'IF-8 · 개인 식별 정보(PII) 검출 시 마스킹 및 전송 통제', sub: '주민번호·여권번호 검출 시 S등급 승인 대기 강제' },
  { name: 'IF-14 · 사내 등록 기밀 키워드 외부 전송 차단', sub: '비밀 표기 및 기밀 코드명 검출 시 즉각 C등급 차단' },
  { name: 'CD-11 · 인코딩 우회 프롬프트 인젝션 탐지 및 무력화', sub: 'Base64/URL 인코딩 및 공백 분리 악성 프롬프트 정규화 차단' },
  { name: 'CD-5 · 실행 파일 위장 및 매직 넘버 검사', sub: 'MZ, ELF, Shell 실행 헤더 위장 파일 업로드 격리' },
]

const GRADE_LABEL = { C: 'C 기밀', S: 'S 민감', O: 'O 공개' } as const

function latency(job: RecentOperationsJob) {
  return job.processingTimeMs == null ? '-' : `${(job.processingTimeMs / 1000).toFixed(2)}s`
}

export function OperationsDashboardPage() {
  const navigate = useNavigate()
  const { session } = useAuth()
  const { dashboard, isLoading, errorCode, refresh } = useOperations('live', session?.role)
  const [filterTab, setFilterTab] = useState<'ALL' | 'C' | 'S' | 'O'>('ALL')

  const dist = useMemo(() => {
    const map = { C: 0, S: 0, O: 0 }
    dashboard?.csoDistribution.forEach((d) => { map[d.grade] = d.count })
    const total = map.C + map.S + map.O
    const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0)
    return { ...map, total, c: pct(map.C), s: pct(map.S), o: pct(map.O) }
  }, [dashboard])

  const stream = (dashboard?.recentJobs ?? []).filter((j) => filterTab === 'ALL' || j.grade === filterTab)
  const q = dashboard?.queue
  const perf = dashboard?.performance
  const sum = dashboard?.summary

  const queueRows = q
    ? [
        { name: '승인 대기', count: q.waitingApproval },
        { name: '검사·파싱·탐지 중', count: q.received + q.inspecting + q.parsing + q.detecting },
        { name: '마스킹·전송·답변 재검사', count: q.masking + q.transmitting + q.postInspecting },
      ]
    : []
  const maxQueue = Math.max(1, ...queueRows.map((r) => r.count))
  const successPct = sum ? Math.round(sum.successRate) : 0

  return (
    <section className="radar-console" aria-labelledby="radar-dashboard-title">
      <header className="radar-head">
        <div className="radar-head__title-group">
          <nav className="radar-head__breadcrumb" aria-label="브레드크럼">
            PASSBOX <span>/</span> 대시보드 <span>/</span> <strong>Radar</strong>
          </nav>
          <h1 id="radar-dashboard-title" className="radar-head__title">운영 대시보드 · Radar 보안 관제</h1>
          <p className="radar-head__sub">
            국가 망 보안체계(N2SF) 기준 문서 등급 판정 현황 · 서버 집계{dashboard ? ` ${new Date(dashboard.generatedAt).toLocaleString('ko-KR')}` : ''}
          </p>
        </div>
        <div className="radar-head__actions">
          <button type="button" className="radar-head__filter-btn" onClick={() => void refresh()} disabled={isLoading}>새로고침</button>
          <button type="button" className="radar-btn-primary" onClick={() => navigate('/upload')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
            새 문서 검사
          </button>
        </div>
      </header>

      {errorCode && <p className="radar-head__sub" role="alert">대시보드를 불러오지 못했습니다 ({errorCode}). ADMIN·OPERATOR 권한이 필요합니다.</p>}
      {isLoading && !dashboard && <p className="radar-head__sub" aria-busy="true">불러오는 중입니다…</p>}

      {dashboard && sum && q && perf && (
        <>
          <div className="radar-kpis">
            <div className="radar-kpi">
              <div className="radar-kpi__header"><span className="radar-kpi__label">총 요청</span><span className="radar-kpi__pill radar-kpi__pill--neutral">전체 누적</span></div>
              <p className="radar-kpi__value">{sum.totalRequests}건</p>
              <p className="radar-kpi__meta">처리 중 {sum.processingRequests}건 · 실패 {sum.failedRequests}건</p>
            </div>
            <div className="radar-kpi">
              <div className="radar-kpi__header"><span className="radar-kpi__label">처리 완료</span><span className="radar-kpi__pill radar-kpi__pill--success">완료율 {successPct}%</span></div>
              <p className="radar-kpi__value">{sum.completedRequests}건</p>
              <p className="radar-kpi__meta">요청~종료 평균 {(perf.averageProcessingTimeMs / 1000).toFixed(1)}s · p95 {(perf.p95ProcessingTimeMs / 1000).toFixed(1)}s (사람 확인 시간 포함)</p>
            </div>
            <div className="radar-kpi is-warn">
              <div className="radar-kpi__header"><span className="radar-kpi__label">승인 대기</span><span className="radar-kpi__pill radar-kpi__pill--warning">4h SLA</span></div>
              <p className="radar-kpi__value">{q.waitingApproval}건</p>
              <p className="radar-kpi__meta">담당자 확인 필요</p>
            </div>
            <div className="radar-kpi is-danger">
              <div className="radar-kpi__header"><span className="radar-kpi__label">전송 차단</span><span className="radar-kpi__pill radar-kpi__pill--danger">C 기밀 {dist.C}건</span></div>
              <p className="radar-kpi__value">{sum.blockedRequests}건</p>
              <p className="radar-kpi__meta">시간당 처리량 {perf.throughputPerHour}건</p>
            </div>
          </div>

          <div className="radar-analytics">
            <div className="radar-card">
              <div className="radar-card__head">
                <h2 className="radar-card__title">N2SF 등급 분포</h2>
                <span className="radar-card__desc">표 2-8 C/S/O 업무정보 분류 기준 · 판정 {dist.total}건</span>
              </div>
              <div className="radar-spectrum-bar" aria-label="C/S/O 등급 비율 바">
                <div className="radar-spectrum-seg--o" style={{ width: `${dist.o}%` }} title={`O등급: ${dist.o}%`} />
                <div className="radar-spectrum-seg--s" style={{ width: `${dist.s}%` }} title={`S등급: ${dist.s}%`} />
                <div className="radar-spectrum-seg--c" style={{ width: `${dist.c}%` }} title={`C등급: ${dist.c}%`} />
              </div>
              <div className="radar-spectrum-legends">
                {([['o', 'O 공개', dist.O, dist.o], ['s', 'S 민감', dist.S, dist.s], ['c', 'C 기밀', dist.C, dist.c]] as const).map(([k, name, n, p]) => (
                  <div className="radar-legend" key={k}>
                    <span className={`radar-legend__dot radar-legend__dot--${k}`} />
                    <span className="radar-legend__name">{name}</span>
                    <div className="radar-legend__stat"><strong>{n}건</strong><small>{p}%</small></div>
                  </div>
                ))}
              </div>
            </div>

            <div className="radar-card">
              <div className="radar-card__head">
                <h2 className="radar-card__title">처리 대기열</h2>
                <span className="radar-card__desc">현재 진행 중인 요청 {q.totalQueued}건</span>
              </div>
              <div className="radar-triggers">
                {queueRows.map((row) => (
                  <div key={row.name} className="radar-trigger-row">
                    <div className="radar-trigger-info"><span>{row.name}</span><span>{row.count}건</span></div>
                    <div className="radar-trigger-track"><div className="radar-trigger-fill" style={{ width: `${(row.count / maxQueue) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="radar-stream">
            <div className="radar-stream__head">
              <div>
                <h2 className="radar-stream__title">최근 보안 판정 내역</h2>
                <p className="radar-head__sub">서버에 기록된 최근 요청 {dashboard.recentJobs.length}건</p>
              </div>
              <div className="radar-stream__tabs" role="tablist" aria-label="등급 필터">
                {(['ALL', 'C', 'S', 'O'] as const).map((tab) => (
                  <button key={tab} type="button" className={`radar-stream__tab ${filterTab === tab ? 'is-active' : ''}`} onClick={() => setFilterTab(tab)}>
                    {tab === 'ALL' ? '전체 내역' : `${GRADE_LABEL[tab]} (${dist[tab]})`}
                  </button>
                ))}
              </div>
            </div>
            <div className="radar-table-wrap">
              <table className="radar-table">
                <thead>
                  <tr><th>등급</th><th>문서명</th><th>요청 ID</th><th>처리시간</th><th>처리 상태</th><th>조치</th></tr>
                </thead>
                <tbody>
                  {stream.length === 0 && <tr><td colSpan={6}>해당하는 내역이 없습니다.</td></tr>}
                  {stream.map((job) => (
                    <tr key={job.jobId}>
                      <td><span className={`radar-badge-${job.grade.toLowerCase()}`}>{GRADE_LABEL[job.grade]}</span></td>
                      <td><div className="radar-table__doc"><span>{job.fileNameDisplay}</span></div></td>
                      <td><span className="radar-chip">{job.requestId}</span></td>
                      <td style={{ color: '#697386', fontVariantNumeric: 'tabular-nums' }}>{latency(job)}</td>
                      <td style={{ fontWeight: 600 }}>{job.currentStep || job.status}</td>
                      <td><button type="button" className="radar-action-link" onClick={() => navigate(`/analysis/${job.jobId}`)}>상세보기 →</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <div className="radar-rules">
        <div className="radar-rules__head">
          <div>
            <h2 className="radar-card__title">적용 중인 보안 통제</h2>
            <p className="radar-head__sub">게이트웨이 연계 구간 ③에서 코드로 강제되는 통제 (N2SF 해설서 항목)</p>
          </div>
          <button type="button" className="radar-action-link" onClick={() => navigate('/admin/policy')}>정책 규칙 관리 →</button>
        </div>
        <div className="radar-triggers">
          {RULES.map((rule) => (
            <div key={rule.name} className="radar-rule-item">
              <div className="radar-rule-info">
                <span className="radar-rule-name">{rule.name}</span>
                <span className="radar-rule-sub">{rule.sub}</span>
              </div>
              <span className="radar-toggle-active">적용 중</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
