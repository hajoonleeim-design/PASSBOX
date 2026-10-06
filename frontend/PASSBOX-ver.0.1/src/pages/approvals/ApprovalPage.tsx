import { useCallback, useEffect, useState } from 'react'
import { decideApproval, getApprovalHistory, getMaskedPayloadPreview, getPendingApprovals, type ApprovalItem, type MaskedPayloadPreview } from '../../api/approvals'
import type { ApiError } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { useAuth } from '../../hooks/useAuth'
import { usePermission } from '../../hooks/usePermission'
import { RetryableApprovalsPanel } from '../../components/security/RetryableApprovalsPanel'
import { Modal } from '../../components/common/Modal'
import { paginate } from '../../utils/paginate'

const HISTORY_PAGE_SIZE = 10
type ApprovalHistoryRow = ApprovalItem & { id: string }

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

function statusLabel(item: ApprovalItem) {
  if (item.status === 'PENDING') return '승인 대기'
  if (item.status === 'APPROVED') return '승인 완료'
  if (item.status === 'REJECTED') return '반려 완료'
  return item.status
}

export function ApprovalPage() {
  const { session } = useAuth()
  const isApprover = usePermission(['APPROVER', 'SECURITY_ADMIN', 'ADMIN'])
  const [items, setItems] = useState<ApprovalItem[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [actingId, setActingId] = useState<number | null>(null)
  const [comments, setComments] = useState<Record<number, string>>({})
  const [error, setError] = useState<ApiError | null>(null)
  const [lastAction, setLastAction] = useState<ApprovalItem | null>(null)
  const [history, setHistory] = useState<ApprovalItem[]>([])
  const [isHistoryLoading, setIsHistoryLoading] = useState(true)
  const [historyPage, setHistoryPage] = useState(1)
  const [preview, setPreview] = useState<MaskedPayloadPreview | null>(null)
  const [previewLoadingId, setPreviewLoadingId] = useState<number | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const loadApprovals = useCallback(async () => {
    if (!isApprover) {
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      setItems(await getPendingApprovals())
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setIsLoading(false)
    }
  }, [isApprover])

  const loadHistory = useCallback(async () => {
    if (!isApprover) {
      setIsHistoryLoading(false)
      return
    }
    setIsHistoryLoading(true)
    try {
      setHistory(await getApprovalHistory())
    } catch {
      // 전송 기록은 보조 정보라 조회가 실패해도 승인 큐 자체는 계속 쓸 수 있게 둔다.
    } finally {
      setIsHistoryLoading(false)
    }
  }, [isApprover])

  useEffect(() => {
    void loadApprovals()
    void loadHistory()
  }, [loadApprovals, loadHistory])

  async function handleDecision(item: ApprovalItem, action: 'approve' | 'reject') {
    setActingId(item.approvalId)
    setError(null)
    setLastAction(null)
    try {
      const updated = await decideApproval(item.approvalId, action, comments[item.approvalId])
      setItems((current) => current?.filter((approval) => approval.approvalId !== item.approvalId) ?? [])
      setLastAction(updated)
      void loadHistory()
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setActingId(null)
    }
  }

  async function handlePreview(item: ApprovalItem) {
    setPreviewLoadingId(item.approvalId)
    setPreviewError(null)
    try {
      setPreview(await getMaskedPayloadPreview(item.approvalId))
    } catch (requestError) {
      setPreviewError((requestError as ApiError).message ?? '마스킹 내용을 불러오지 못했습니다.')
    } finally {
      setPreviewLoadingId(null)
    }
  }

  if (!isApprover) {
    return (
      <section className="approval-page" aria-live="polite">
        <div className="page-title-row">
          <div>
            <p className="eyebrow">외부 전송 승인</p>
            <h1>승인 권한이 없습니다.</h1>
            <p>APPROVER, SECURITY_ADMIN 또는 ADMIN 권한이 있는 사용자만 접근할 수 있습니다.</p>
          </div>
        </div>
        <Card className="section-gap">
          <ErrorState label="현재 계정은 승인 권한이 없습니다. 승인 권한이 부여된 계정으로 로그인해 주세요." />
        </Card>
        <p className="approval-session-note">현재 로그인: {session?.displayName} · {session?.role}</p>
      </section>
    )
  }

  if (isLoading && !items) return <LoadingState label="승인 대기 요청을 불러오는 중입니다." />
  if (error?.status === 403) {
    return <section className="state-action-page"><h1>승인 권한이 없습니다.</h1><ErrorState label="APPROVER, SECURITY_ADMIN 또는 ADMIN 권한이 있는 사용자만 접근할 수 있습니다." /></section>
  }
  if (error && !items) {
    return <section className="state-action-page"><h1>승인 요청을 불러오지 못했습니다.</h1><ErrorState label={error.message} /><Button onClick={() => void loadApprovals()}>다시 조회</Button></section>
  }

  const historyRows: ApprovalHistoryRow[] = history.map((item) => ({ ...item, id: String(item.approvalId) }))
  const historySlice = paginate(historyRows, historyPage, HISTORY_PAGE_SIZE)
  const historyColumns: DataTableColumn<ApprovalHistoryRow>[] = [
    { key: 'document', header: '문서 ID', render: (item) => `#${item.documentId}` },
    { key: 'provider', header: 'Provider / Model', render: (item) => <code>{item.provider} / {item.model}</code> },
    { key: 'decision', header: '결정', render: (item) => <span className={`badge ${item.status === 'APPROVED' ? 'badge--success' : 'badge--danger'}`}>{statusLabel(item)}</span> },
    { key: 'transmission', header: '전송 상태', render: (item) => item.transmissionStatus },
    { key: 'postInspection', header: 'Post-Inspector', render: (item) => item.postInspectionStatus ?? '-' },
    { key: 'decidedBy', header: '결정자', render: (item) => item.decidedBy ? `User ID ${item.decidedBy}` : '-' },
    { key: 'decidedAt', header: '결정 시각', render: (item) => item.decidedAt ? formatDate(item.decidedAt) : '-' },
  ]

  return (
    <section className="approval-page" aria-live="polite">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">외부 전송 승인</p>
          <h1>S등급 외부 전송 승인</h1>
          <p>민감정보가 포함된 문서의 외부 AI 전송 요청을 검토하고 처리합니다.</p>
          <p className="approval-note">
            사용자가 S등급 문서를 외부 AI로 전송 요청하면 이 목록에 자동으로 올라옵니다.
            "승인 후 전송"을 누르면 마스킹된 payload가 즉시 Gateway로 전송되고, "반려"를 누르면 전송이 중단됩니다.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void loadApprovals()} disabled={isLoading}>
          {isLoading ? '조회 중' : '새로고침'}
        </Button>
      </div>

      {error && <div className="section-gap"><Alert variant="danger" title="승인 요청 처리 실패">{error.message}</Alert></div>}
      {lastAction && (
        <div className="section-gap">
          <Alert variant={lastAction.status === 'APPROVED' ? 'success' : 'warning'} title={`${statusLabel(lastAction)} 처리되었습니다.`}>
            문서 ID {lastAction.documentId} · 전송 상태 {lastAction.transmissionStatus}
            {lastAction.response && <p className="approval-response">{lastAction.response}</p>}
          </Alert>
        </div>
      )}

      <RetryableApprovalsPanel />
      {!items || items.length === 0 ? (
        <Card className="section-gap"><EmptyState label="현재 대기 중인 승인 요청이 없습니다." /></Card>
      ) : (
        <div className="approval-list">
          {items.map((item) => (
            <Card className={`approval-card ${item.isEscalated ? 'approval-card--escalated' : ''}`} key={item.approvalId}>
              <div className="page-title-row">
                <div>
                  <p className="eyebrow">승인 요청 #{item.approvalId}</p>
                  <h2>문서 ID {item.documentId}</h2>
                </div>
                <div className="approval-card__badges">
                  {item.isEscalated && <span className="badge badge--danger">⚠ {item.hoursPending}시간 경과 · 에스컬레이션</span>}
                  <span className="badge badge--warning">승인 대기</span>
                </div>
              </div>

              <dl className="info-list">
                <div><dt>요청 시각</dt><dd>{formatDate(item.createdAt)}</dd></div>
                <div><dt>요청 사용자</dt><dd>User ID {item.requestedBy}</dd></div>
                <div><dt>Provider / Model</dt><dd><code>{item.provider} / {item.model}</code></dd></div>
                <div><dt>마스킹 버전</dt><dd><code>{item.maskingVersion}</code></dd></div>
                <div>
                  <dt>탐지 유형</dt>
                  <dd>
                    {item.maskingCategories.length === 0
                      ? '탐지된 마스킹 대상 없음'
                      : <div className="approval-tags">{item.maskingCategories.map((category) => <span className="badge badge--warning" key={category}>{category}</span>)}</div>}
                  </dd>
                </div>
              </dl>

              <p className="approval-note">승인 전에 외부 AI로 전달될 마스킹 텍스트를 확인하세요. 승인하면 아래 미리보기와 같은 내용이 Gateway로 전송됩니다.</p>
              <div className="form-actions section-gap">
                <Button variant="secondary" onClick={() => void handlePreview(item)} disabled={previewLoadingId !== null || actingId !== null}>
                  {previewLoadingId === item.approvalId ? '불러오는 중…' : '전송 전 마스킹 내용 확인'}
                </Button>
                {previewError && <span role="alert" className="form-error">{previewError}</span>}
              </div>
              <label className="form-field section-gap">
                처리 의견 <small>선택 사항</small>
                <textarea
                  className="form-control"
                  rows={3}
                  value={comments[item.approvalId] ?? ''}
                  onChange={(event) => setComments((current) => ({ ...current, [item.approvalId]: event.target.value }))}
                  placeholder="승인 또는 반려 사유를 입력하세요."
                  disabled={actingId === item.approvalId}
                />
              </label>
              <div className="form-actions section-gap">
                <Button onClick={() => void handleDecision(item, 'approve')} disabled={actingId !== null}>
                  {actingId === item.approvalId ? '처리 중' : '승인 후 전송'}
                </Button>
                <Button variant="danger" onClick={() => void handleDecision(item, 'reject')} disabled={actingId !== null}>
                  반려
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="page-title-row section-gap">
        <div>
          <h2>전송 기록</h2>
          <p>승인하거나 반려해서 처리가 끝난 S등급 요청입니다. AI 응답 원문은 승인 직후 한 번만 보여주고 저장하지 않아 이 기록에는 나오지 않습니다.</p>
        </div>
      </div>
      {isHistoryLoading && historyRows.length === 0 ? (
        <LoadingState label="전송 기록을 불러오는 중입니다." />
      ) : historyRows.length === 0 ? (
        <Card><EmptyState label="아직 처리된 승인 요청이 없습니다." /></Card>
      ) : (
        <>
          <DataTable columns={historyColumns} rows={historySlice.pageItems} />
          <Pagination page={historySlice.safePage} pageCount={historySlice.pageCount} pageSize={HISTORY_PAGE_SIZE} totalCount={historyRows.length} onPageChange={setHistoryPage} />
        </>
      )}

      <p className="approval-session-note">현재 로그인: {session?.displayName} · {session?.role}</p>
      {preview && <Modal title={`전송 전 마스킹 내용 · 요청 #${preview.approvalId}`} onClose={() => setPreview(null)}>
        <p>아래 내용이 승인 시 외부 AI에 전달됩니다. 원본 문서 파일이 아니라 전송용 텍스트 미리보기입니다.</p>
        <p><small>마스킹 버전: {preview.maskingVersion} · 탐지 유형: {preview.maskingCategories.join(', ') || '없음'}</small></p>
        <pre style={{ maxHeight: '55vh', overflow: 'auto', padding: 16, border: '1px solid var(--color-border)', borderRadius: 8, color: 'var(--color-text)', background: 'var(--color-surface-elevated)', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', font: 'inherit' }}>{preview.maskedPayload || '(전송할 텍스트가 비어 있습니다)'}</pre>
        <div className="modal-actions"><Button variant="secondary" onClick={() => setPreview(null)}>닫기</Button></div>
      </Modal>}
    </section>
  )
}
