import { useCallback, useEffect, useState } from 'react'
import { getRetryableApprovals, retryApproval, type ApprovalItem } from '../../api/approvals'
import { Alert } from '../common/Alert'
import { Button } from '../common/Button'
import { Card } from '../common/Card'

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

export function RetryableApprovalsPanel() {
  const [items, setItems] = useState<ApprovalItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [actingId, setActingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      setItems(await getRetryableApprovals())
    } catch {
      setError('재시도 가능한 Gateway 전송 건을 조회하지 못했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleRetry(approvalId: number) {
    setActingId(approvalId)
    setError('')
    setSuccess('')
    try {
      const updated = await retryApproval(approvalId)
      setItems((current) => current.filter((item) => item.approvalId !== approvalId))
      setSuccess(`문서 ID ${updated.documentId} Gateway 재전송이 완료되었습니다.`)
    } catch {
      setError('Gateway 재전송에 실패했습니다. 전송 상태를 다시 확인해 주세요.')
    } finally {
      setActingId(null)
    }
  }

  if (isLoading || (!error && items.length === 0)) return null

  return (
    <section className="approval-retry-panel section-gap" aria-live="polite">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">RETRYABLE TRANSMISSIONS</p>
          <h2>Gateway 재시도 대기</h2>
          <p>승인되었지만 전송에 실패한 건입니다. 원문이 아닌 마스킹 Payload만 재전송합니다.</p>
        </div>
        <Button variant="secondary" onClick={() => void load()} disabled={isLoading}>새로고침</Button>
      </div>
      {error && <Alert variant="danger" title="재시도 조회/처리 실패">{error}</Alert>}
      {success && <Alert variant="success" title="재전송 완료">{success}</Alert>}
      <div className="approval-retry-list">
        {items.map((item) => (
          <Card key={item.approvalId} className="approval-retry-card">
            <div className="page-title-row">
              <div>
                <p className="eyebrow">APPROVAL #{item.approvalId}</p>
                <h3>문서 ID {item.documentId}</h3>
              </div>
              <span className="badge badge--danger">전송 실패</span>
            </div>
            <p><code>{item.provider} / {item.model}</code></p>
            <small>승인 시각: {item.decidedAt ? formatDate(item.decidedAt) : formatDate(item.createdAt)}</small>
            <Button onClick={() => void handleRetry(item.approvalId)} disabled={actingId !== null}>
              {actingId === item.approvalId ? '재전송 중' : 'Gateway 재전송'}
            </Button>
          </Card>
        ))}
      </div>
    </section>
  )
}
