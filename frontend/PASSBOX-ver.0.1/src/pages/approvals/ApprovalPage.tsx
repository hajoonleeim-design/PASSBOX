import { useCallback, useEffect, useState } from 'react'
import { decideApproval, getPendingApprovals, type ApprovalItem } from '../../api/approvals'
import type { ApiError } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { useAuth } from '../../hooks/useAuth'
import { RetryableApprovalsPanel } from '../../components/security/RetryableApprovalsPanel'

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
  const [items, setItems] = useState<ApprovalItem[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [actingId, setActingId] = useState<number | null>(null)
  const [comments, setComments] = useState<Record<number, string>>({})
  const [error, setError] = useState<ApiError | null>(null)
  const [lastAction, setLastAction] = useState<ApprovalItem | null>(null)

  const loadApprovals = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setItems(await getPendingApprovals())
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadApprovals()
  }, [loadApprovals])

  async function handleDecision(item: ApprovalItem, action: 'approve' | 'reject') {
    setActingId(item.approvalId)
    setError(null)
    setLastAction(null)
    try {
      const updated = await decideApproval(item.approvalId, action, comments[item.approvalId])
      setItems((current) => current?.filter((approval) => approval.approvalId !== item.approvalId) ?? [])
      setLastAction(updated)
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setActingId(null)
    }
  }

  if (isLoading && !items) return <LoadingState label="승인 대기 요청을 불러오는 중입니다." />
  if (error?.status === 403) {
    return <section><h1>승인 권한이 없습니다.</h1><ErrorState label="APPROVER, SECURITY_ADMIN 또는 ADMIN 권한이 있는 사용자만 접근할 수 있습니다." /></section>
  }
  if (error && !items) {
    return <section><h1>승인 요청을 불러오지 못했습니다.</h1><ErrorState label={error.message} /><Button onClick={() => void loadApprovals()}>다시 조회</Button></section>
  }

  return (
    <section className="approval-page" aria-live="polite">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">외부 전송 승인</p>
          <h1>S등급 외부 전송 승인</h1>
          <p>민감정보가 포함된 문서의 외부 AI 전송 요청을 검토하고 처리합니다.</p>
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
            <Card className="approval-card" key={item.approvalId}>
              <div className="page-title-row">
                <div>
                  <p className="eyebrow">승인 요청 #{item.approvalId}</p>
                  <h2>문서 ID {item.documentId}</h2>
                </div>
                <span className="badge badge--warning">승인 대기</span>
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

              <p className="approval-note">원문은 승인 화면에 표시하지 않습니다. 승인 후에도 마스킹된 payload만 Gateway로 전달됩니다.</p>
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
      <p className="approval-session-note">현재 로그인: {session?.displayName} · {session?.role}</p>
    </section>
  )
}
