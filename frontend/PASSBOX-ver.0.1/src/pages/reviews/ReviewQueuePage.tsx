// C등급(전송 차단) 문서에 대한 재검토 요청을 담당자가 확인하고 등급을 재조정하거나 반려합니다.
import { useCallback, useEffect, useState } from 'react'
import { decideReviewRequest, getPendingReviewRequests } from '../../api/reviewRequests'
import type { ApiError } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { useAuth } from '../../hooks/useAuth'
import { usePermission } from '../../hooks/usePermission'
import type { ReviewRequestItem } from '../../types/reviewRequest'
import type { SecurityGrade } from '../../types/security'

const formatDate = (value: string) => new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

export function ReviewQueuePage() {
  const { session } = useAuth()
  const isReviewer = usePermission(['OPERATOR', 'SECURITY_ADMIN', 'ADMIN'])
  const [items, setItems] = useState<ReviewRequestItem[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [actingId, setActingId] = useState<number | null>(null)
  const [grades, setGrades] = useState<Record<number, SecurityGrade>>({})
  const [comments, setComments] = useState<Record<number, string>>({})
  const [error, setError] = useState<ApiError | null>(null)
  const [lastAction, setLastAction] = useState<ReviewRequestItem | null>(null)

  const loadItems = useCallback(async () => {
    if (!isReviewer) {
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      setItems(await getPendingReviewRequests())
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setIsLoading(false)
    }
  }, [isReviewer])

  useEffect(() => { void loadItems() }, [loadItems])

  async function handleDecision(item: ReviewRequestItem, action: 'approve' | 'reject') {
    setActingId(item.reviewRequestId)
    setError(null)
    setLastAction(null)
    try {
      const updated = await decideReviewRequest(item.reviewRequestId, {
        action,
        comment: comments[item.reviewRequestId],
        newGrade: action === 'approve' ? (grades[item.reviewRequestId] ?? 'O') : undefined,
      })
      setItems((current) => current?.filter((candidate) => candidate.reviewRequestId !== item.reviewRequestId) ?? [])
      setLastAction(updated)
    } catch (requestError) {
      setError(requestError as ApiError)
    } finally {
      setActingId(null)
    }
  }

  if (!isReviewer) {
    return (
      <section aria-live="polite">
        <div className="page-title-row">
          <div>
            <p className="eyebrow">C등급 재검토</p>
            <h1>재검토 권한이 없습니다.</h1>
            <p>OPERATOR, SECURITY_ADMIN 또는 ADMIN 권한이 있는 사용자만 접근할 수 있습니다.</p>
          </div>
        </div>
        <Card className="section-gap"><ErrorState label="현재 계정은 재검토 권한이 없습니다." /></Card>
        <p className="approval-session-note">현재 로그인: {session?.displayName} · {session?.role}</p>
      </section>
    )
  }

  if (isLoading && !items) return <LoadingState label="재검토 요청을 불러오는 중입니다." />
  if (error?.status === 403) {
    return <section className="state-action-page"><h1>재검토 권한이 없습니다.</h1><ErrorState label="OPERATOR, SECURITY_ADMIN 또는 ADMIN 권한이 있는 사용자만 접근할 수 있습니다." /></section>
  }
  if (error && !items) {
    return <section className="state-action-page"><h1>재검토 요청을 불러오지 못했습니다.</h1><ErrorState label={error.message} /><Button onClick={() => void loadItems()}>다시 조회</Button></section>
  }

  return (
    <section aria-live="polite">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">C등급 재검토</p>
          <h1>C등급 재검토 요청</h1>
          <p>전송 차단(C등급) 판정에 대해 사용자가 신고한 재검토 요청을 확인하고 등급을 재조정하거나 반려합니다.</p>
        </div>
        <Button variant="secondary" onClick={() => void loadItems()} disabled={isLoading}>{isLoading ? '조회 중' : '새로고침'}</Button>
      </div>

      {error && <div className="section-gap"><Alert variant="danger" title="처리 실패">{error.message}</Alert></div>}
      {lastAction && (
        <div className="section-gap">
          <Alert variant={lastAction.status === 'APPROVED' ? 'success' : 'warning'} title={`${lastAction.status === 'APPROVED' ? '승인' : '반려'} 처리되었습니다.`}>
            문서 ID {lastAction.documentId}
            {lastAction.status === 'APPROVED' && ` · 재조정 등급 ${lastAction.resolvedGrade}`}
          </Alert>
        </div>
      )}

      {!items || items.length === 0 ? (
        <Card className="section-gap"><EmptyState label="현재 대기 중인 재검토 요청이 없습니다." /></Card>
      ) : (
        <div className="approval-list">
          {items.map((item) => (
            <Card className="approval-card" key={item.reviewRequestId}>
              <div className="page-title-row">
                <div>
                  <p className="eyebrow">재검토 요청 #{item.reviewRequestId}</p>
                  <h2>{item.fileName}</h2>
                </div>
                <span className="badge badge--danger">원 등급 {item.originalGrade}</span>
              </div>

              <dl className="info-list">
                <div><dt>요청 시각</dt><dd>{formatDate(item.createdAt)}</dd></div>
                <div><dt>요청 사용자</dt><dd>{item.requestedByName}</dd></div>
                <div><dt>신고 사유</dt><dd>{item.reason}</dd></div>
                <div><dt>재학습 후보 표시</dt><dd>{item.flagForRetraining ? '예' : '아니오'}</dd></div>
              </dl>

              <label className="form-field section-gap">
                재조정 등급
                <select
                  className="form-control"
                  value={grades[item.reviewRequestId] ?? 'O'}
                  onChange={(event) => setGrades((current) => ({ ...current, [item.reviewRequestId]: event.target.value as SecurityGrade }))}
                  disabled={actingId === item.reviewRequestId}
                >
                  <option value="C">C · 기밀 · 외부 전송 차단 유지</option>
                  <option value="S">S · 민감 · 승인 후 전송</option>
                  <option value="O">O · 공개 · 정책 검증 후 전송</option>
                </select>
              </label>
              <label className="form-field section-gap">
                처리 의견 <small>선택 사항</small>
                <textarea
                  className="form-control"
                  rows={3}
                  value={comments[item.reviewRequestId] ?? ''}
                  onChange={(event) => setComments((current) => ({ ...current, [item.reviewRequestId]: event.target.value }))}
                  placeholder="재조정 또는 반려 사유를 입력하세요."
                  disabled={actingId === item.reviewRequestId}
                />
              </label>
              <div className="form-actions section-gap">
                <Button onClick={() => void handleDecision(item, 'approve')} disabled={actingId !== null}>
                  {actingId === item.reviewRequestId ? '처리 중' : '승인 · 등급 재조정'}
                </Button>
                <Button variant="danger" onClick={() => void handleDecision(item, 'reject')} disabled={actingId !== null}>
                  반려 · 원 등급 유지
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
