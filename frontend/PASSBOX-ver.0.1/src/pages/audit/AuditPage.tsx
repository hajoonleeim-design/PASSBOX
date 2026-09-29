// Request ID를 기준으로 감사 기록을 조회하고, 조회 결과를 PDF로 내려받는 화면입니다.
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { generateAuditPdfSource as generateAuditPdf } from '../../api/auditSource'
import { Alert } from '../../components/common/Alert'
import { Badge, type BadgeVariant } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { FormField, TextInput } from '../../components/common/FormControls'
import { PageOnboardingTour, type OnboardingTourStep } from '../../components/common/PageOnboardingTour'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { GradeBadge } from '../../components/security/GradeBadge'
import { useAudit } from '../../hooks/useAudit'
import { useAuth } from '../../hooks/useAuth'
import type { AuditEvent } from '../../types/audit'
import type { ApprovalHistoryEntry } from '../../types/decision'

const auditOnboardingSteps: OnboardingTourStep[] = [
  { id: 'lookup', target: '[data-onboarding-target="audit-lookup"]', title: 'Request ID로 감사 이력을 조회하세요', description: '요청에 연결된 처리 이력과 증적을 확인하려면 Request ID를 입력한 뒤 조회를 선택하세요.' },
  { id: 'timeline', target: '[data-onboarding-target="audit-timeline"]', title: '처리 Timeline을 확인하세요', description: '요청 생성부터 분석, 판정, 승인과 보안 검증까지의 처리 순서와 수행 주체를 시간순으로 확인할 수 있습니다.' },
  { id: 'evidence', target: '[data-onboarding-target="audit-evidence"]', title: 'Evidence 요약을 확인하세요', description: '파일 내용이나 AI 원문 대신 파일 유형, 해시, 정책 버전, 승인 및 Post-Inspector 상태 같은 안전한 메타데이터만 제공합니다.' },
  { id: 'report', target: '[data-onboarding-target="audit-pdf"]', title: 'PDF 보고서를 생성하세요', description: '감사 메타데이터를 PDF 보고서로 생성할 수 있습니다. 원본 문서와 AI 원문은 보고서에 포함되지 않습니다.' },
]

const formatDate = (value: string) => new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

const eventVariant = (status: string): BadgeVariant => {
  if (status.includes('BLOCK') || status.includes('FAILED') || status.includes('REJECT')) return 'danger'
  if (status.includes('WAIT') || status.includes('INSPECT')) return 'warning'
  if (status.includes('COMPLETED') || status.includes('APPROVED') || status.includes('VERIFIED')) return 'success'
  return 'info'
}

const eventName = (type: string) => ({
  REQUEST_CREATED: '요청 생성', FILE_VALIDATED: '파일 검증 완료', ANALYSIS_STARTED: '분석 시작', ANALYSIS_COMPLETED: '분석 완료', ANALYSIS_BLOCKED: '분석 차단', DECISION_CREATED: 'C/S/O 판정', APPROVAL_REQUESTED: '승인 요청', APPROVED: '승인', REJECTED: '반려', PAYLOAD_VALIDATED: 'Payload 검증', AI_TRANSMITTED: 'AI 전송', AI_RESPONSE_RECEIVED: 'AI 응답 수신', POST_INSPECTION_STARTED: 'Post-Inspector 시작', POST_INSPECTION_VERIFIED: 'Post-Inspector 완료', POST_INSPECTION_BLOCKED: 'Post-Inspector 차단', COMPLETED: '처리 완료', FAILED: '처리 실패',
}[type] ?? type)

const approvalColumns: DataTableColumn<ApprovalHistoryEntry>[] = [
  { key: 'action', header: '결과', render: (item) => item.action === 'APPROVED' ? '승인' : '반려' },
  { key: 'actor', header: '처리자', render: (item) => item.actor.displayName },
  { key: 'role', header: '역할', render: (item) => item.actor.role },
  { key: 'time', header: '처리 시각', render: (item) => formatDate(item.actedAt) },
  { key: 'reason', header: '사유', render: (item) => item.reason ?? 'N/A' },
]

function Timeline({ events }: { events: AuditEvent[] }) {
  return <ol className="audit-timeline">{events.map((event) => <li key={event.eventId}><span className="audit-timeline__marker" aria-hidden="true">✓</span><div><div className="timeline-row"><strong>{eventName(event.eventType)}</strong><Badge variant={eventVariant(event.status)}>{event.status}</Badge></div><p>{event.description}</p><small>{formatDate(event.timestamp)} · {event.actor} · {event.actorRole}</small></div></li>)}</ol>
}

export function AuditPage() {
  const { requestId } = useParams()
  const navigate = useNavigate()
  const { session } = useAuth()
  const actor = session ? { userId: session.userId, role: session.role } : null
  const { audit, isLoading, errorCode, refresh } = useAudit(requestId, actor)
  const [query, setQuery] = useState(requestId ?? '')
  const [pdfError, setPdfError] = useState('')
  const [isPdfGenerating, setIsPdfGenerating] = useState(false)

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const next = query.trim()
    if (next) navigate(`/audit/${encodeURIComponent(next)}`)
  }

  function restartOnboarding() {
    window.dispatchEvent(new CustomEvent('passbox:onboarding-restart', { detail: 'passbox:onboarding:audit:v1' }))
  }

  async function downloadPdf() {
    if (!audit || !actor) return
    setPdfError('')
    setIsPdfGenerating(true)
    try {
      const result = await generateAuditPdf(audit.requestId, actor)
      const url = URL.createObjectURL(result.blob)
      const link = document.createElement('a')
      link.href = url
      link.download = result.fileName
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      setPdfError('PDF 보고서를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsPdfGenerating(false)
    }
  }

  const onboarding = <PageOnboardingTour storageKey="passbox:onboarding:audit:v1" steps={auditOnboardingSteps} calloutPlacement="bottom" />
  const lookup = <Card className="audit-lookup" data-onboarding-target="audit-lookup"><form onSubmit={search}><FormField label="Request ID"><TextInput value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Request ID를 입력하세요" /></FormField><Button type="submit">조회</Button></form></Card>

  if (isLoading && !audit) return <section>{lookup}<LoadingState label="감사 기록을 불러오는 중입니다." />{onboarding}</section>
  if (errorCode === 'NOT_FOUND') return <section>{lookup}<h1>감사 기록을 찾을 수 없습니다.</h1><ErrorState label="입력한 Request ID에 해당하는 감사 기록이 없습니다." />{onboarding}</section>
  if (errorCode === 'FORBIDDEN') return <section>{lookup}<h1>권한이 없습니다.</h1><ErrorState label="이 감사 기록을 조회할 권한이 없습니다." />{onboarding}</section>
  if (errorCode || !audit) return <section>{lookup}<h1>감사 기록을 불러오지 못했습니다.</h1><ErrorState label="네트워크 연결을 확인한 후 다시 시도해 주세요." /><Button onClick={() => void refresh()}>다시 시도</Button>{onboarding}</section>

  const evidenceRows = Object.entries({ 파일명: audit.evidence.fileName, '파일 유형': audit.evidence.fileType, '파일 크기': audit.evidence.fileSize, 'SHA-256 Hash': audit.evidence.fileHash, 'Request ID': audit.evidence.requestId, 'Job ID': audit.evidence.jobId ?? 'N/A', '탐지 유형': audit.evidence.detectionType ?? 'N/A', '정책 버전': audit.evidence.policyVersion, '승인 상태': audit.evidence.approvalStatus, 'Post-Inspector': audit.evidence.postInspectionStatus ?? 'N/A', 'Incident ID': audit.evidence.incidentId ?? 'N/A' })

  return <section aria-live="polite">{lookup}<div className="page-title-row"><div><p className="eyebrow">AUDIT & EVIDENCE</p><h1>감사·증적</h1><p>원문이 아닌 처리 이벤트와 메타데이터를 기준으로 요청 이력을 확인합니다.</p></div><div className="table-actions"><Button variant="ghost" onClick={restartOnboarding}>사용 안내 다시 보기</Button><Button data-onboarding-target="audit-pdf" onClick={() => void downloadPdf()} disabled={isPdfGenerating}>{isPdfGenerating ? 'PDF 생성 중' : 'PDF 보고서 생성'}</Button></div></div>{pdfError && <div className="section-gap"><Alert variant="danger" title="PDF 생성 실패">{pdfError}</Alert></div>}<div className="audit-summary-grid"><Card><dl className="info-list"><div><dt>Request ID</dt><dd><code>{audit.requestId}</code></dd></div><div><dt>Job ID</dt><dd>{audit.jobId ?? 'N/A'}</dd></div><div><dt>현재 상태</dt><dd><Badge variant={eventVariant(audit.currentStatus)}>{audit.currentStatus}</Badge></dd></div><div><dt>생성 시각</dt><dd>{formatDate(audit.createdAt)}</dd></div><div><dt>완료 시각</dt><dd>{audit.completedAt ? formatDate(audit.completedAt) : 'N/A'}</dd></div></dl></Card><Card><p className="eyebrow">SECURITY SUMMARY</p><GradeBadge grade={audit.grade} /><p>정책 버전: {audit.policyVersion}</p><p>Incident ID: {audit.incidentId ?? 'N/A'}</p><small>AI 원문 응답과 원본 문서는 감사 화면에 표시하지 않습니다.</small></Card></div><div className="audit-content-grid"><Card data-onboarding-target="audit-timeline"><h2>처리 Timeline</h2><Timeline events={audit.events} /></Card><Card data-onboarding-target="audit-evidence"><h2>Evidence 요약</h2>{evidenceRows.length === 0 ? <EmptyState label="표시할 Evidence가 없습니다." /> : <dl className="evidence-summary">{evidenceRows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}</Card></div><Card className="history-card"><h2>승인 / 반려 이력</h2><DataTable columns={approvalColumns} rows={audit.approvalHistory} emptyMessage="승인 또는 반려 이력이 없습니다." /></Card>{onboarding}</section>
}
