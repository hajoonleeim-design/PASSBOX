// 확정을 기다리는 문서를 여러 건 골라 AI 추천 등급 그대로 한 번에 확정하는 화면입니다.
// 추천과 다른 등급으로는 확정할 수 없고(서버가 막음), 본인이 올린 문서는 고를 수 없습니다.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { bulkConfirmRecommended, getPendingConfirmations, type BulkConfirmResult, type PendingConfirmation } from '../../api/classification'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { EmptyState, LoadingState } from '../../components/common/StateViews'

type Row = PendingConfirmation & { id: string }

const GRADE_LABEL: Record<string, string> = { C: 'C 기밀', S: 'S 민감', O: 'O 공개' }
const formatDate = (value: string) => new Intl.DateTimeFormat('ko-KR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
const percent = (value: number | null) => (value === null ? '-' : `${Math.round(value * 100)}%`)

export function BulkConfirmPage() {
  const [rows, setRows] = useState<Row[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isConfirming, setIsConfirming] = useState(false)
  const [armed, setArmed] = useState(false)
  const [result, setResult] = useState<BulkConfirmResult | null>(null)

  const load = useCallback(async () => {
    try {
      setError('')
      const items = await getPendingConfirmations()
      setRows(items.map((item) => ({ ...item, id: String(item.documentId) })))
      // 이미 처리되어 목록에서 사라진 문서는 선택에서도 뺀다.
      setSelected((current) => new Set([...current].filter((id) => items.some((item) => item.documentId === id && !item.uploadedByMe))))
    } catch {
      setError('확정 대기 문서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const selectable = useMemo(() => rows.filter((row) => !row.uploadedByMe && row.recommendedGrade), [rows])
  const counts = useMemo(() => {
    const byGrade: Record<string, number> = {}
    for (const row of rows.filter((item) => selected.has(item.documentId))) byGrade[row.recommendedGrade ?? '-'] = (byGrade[row.recommendedGrade ?? '-'] ?? 0) + 1
    return byGrade
  }, [rows, selected])

  function toggle(documentId: number) {
    setArmed(false)
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(documentId)) next.delete(documentId)
      else next.add(documentId)
      return next
    })
  }

  function selectGrade(grade: string | null) {
    setArmed(false)
    setSelected(new Set(selectable.filter((row) => grade === null || row.recommendedGrade === grade).map((row) => row.documentId)))
  }

  async function confirm() {
    if (!armed) {
      setArmed(true)
      return
    }
    setIsConfirming(true)
    setError('')
    try {
      const outcome = await bulkConfirmRecommended([...selected])
      setResult(outcome)
      setSelected(new Set())
      setArmed(false)
      await load()
    } catch {
      setError('일괄 확정에 실패했습니다. 잠시 후 다시 시도해 주세요. 일부 문서는 이미 확정되었을 수 있으니 목록을 확인하세요.')
    } finally {
      setIsConfirming(false)
    }
  }

  const columns: DataTableColumn<Row>[] = [
    {
      key: 'select',
      header: '선택',
      render: (row) => (
        <input
          type="checkbox"
          aria-label={`${row.fileName} 선택`}
          checked={selected.has(row.documentId)}
          disabled={row.uploadedByMe || !row.recommendedGrade}
          onChange={() => toggle(row.documentId)}
        />
      ),
    },
    { key: 'file', header: '문서', render: (row) => <span>{row.fileName}{row.uploadedByMe && <small className="table-muted"> · 본인이 올린 문서(제외)</small>}</span> },
    { key: 'grade', header: 'AI 추천', render: (row) => <strong>{row.recommendedGrade ? GRADE_LABEL[row.recommendedGrade] ?? row.recommendedGrade : '추천 없음'}</strong> },
    { key: 'confidence', header: '확신도', render: (row) => percent(row.confidence) },
    { key: 'created', header: '올린 시각', render: (row) => formatDate(row.createdAt) },
  ]

  if (isLoading) return <LoadingState label="확정 대기 문서를 불러오는 중입니다." />

  const selectedCount = selected.size
  const summary = Object.entries(counts).map(([grade, count]) => `${GRADE_LABEL[grade] ?? grade} ${count}건`).join(' · ')

  return (
    <section>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">등급 확정</p>
          <h1>AI 추천대로 일괄 확정</h1>
          <p>
            문서가 많을 때 한 건씩 열지 않고, 믿을 만한 추천을 골라 한 번에 확정합니다.
            추천과 다른 등급으로는 확정할 수 없고, 등급을 바꾸려면 작업 목록에서 개별로 확정하세요.
          </p>
        </div>
        <div className="table-actions">
          <Link to="/analysis/recent" className="button button--secondary">작업 목록으로</Link>
          <Button variant="secondary" onClick={() => void load()}>새로고침</Button>
        </div>
      </div>

      {error && <div className="section-gap"><Alert variant="danger" title="처리 실패">{error}</Alert></div>}
      {result && (
        <div className="section-gap">
          <Alert variant={result.confirmed > 0 ? 'success' : 'warning'} title={`${result.confirmed}건 확정 · ${result.skipped}건 건너뜀`}>
            {result.skipped > 0
              ? result.items.filter((item) => item.result === 'SKIPPED').slice(0, 5).map((item) => `문서 ${item.documentId}: ${item.reason}`).join(' / ')
              : '선택한 문서를 모두 확정했습니다. 확정 기록은 감사 기록에 일괄 확정으로 남습니다.'}
          </Alert>
        </div>
      )}

      {rows.length === 0 ? (
        <Card><EmptyState label="확정을 기다리는 문서가 없습니다." /></Card>
      ) : (
        <>
          <div className="analysis-list-summary">
            <strong>확정 대기 {rows.length}건 · 일괄 선택 가능 {selectable.length}건</strong>
            <span>본인이 올린 문서는 직무 분리를 위해 다른 담당자가 확정해야 합니다.</span>
          </div>
          <div className="table-actions section-gap">
            <Button size="sm" variant="secondary" onClick={() => selectGrade('O')} disabled={!selectable.some((row) => row.recommendedGrade === 'O')}>O 추천만 모두 선택</Button>
            <Button size="sm" variant="secondary" onClick={() => selectGrade(null)} disabled={selectable.length === 0}>선택 가능한 문서 모두 선택</Button>
            <Button size="sm" variant="ghost" onClick={() => selectGrade('__none__')} disabled={selectedCount === 0}>선택 해제</Button>
          </div>
          <DataTable columns={columns} rows={rows} />
          <div className="form-actions section-gap">
            <span>{selectedCount > 0 ? `선택 ${selectedCount}건 (${summary})` : '확정할 문서를 선택하세요.'}</span>
            <Button onClick={() => void confirm()} disabled={selectedCount === 0 || isConfirming}>
              {isConfirming ? '확정 중' : armed ? `정말 ${selectedCount}건을 AI 추천대로 확정` : `선택한 ${selectedCount}건을 AI 추천대로 확정`}
            </Button>
            {armed && !isConfirming && <Button variant="ghost" onClick={() => setArmed(false)}>취소</Button>}
          </div>
          {armed && selected.size > 0 && (
            <Alert variant="warning" title="한 번 더 확인합니다">
              S 추천 문서는 확정 후에도 외부 전송 시 승인자 확인을 거치고, C 추천 문서는 전송이 차단됩니다. O 추천 문서는 승인 없이 전송할 수 있게 되므로, 눌러서 확정하기 전에 목록의 확신도를 확인하세요.
            </Alert>
          )}
        </>
      )}
    </section>
  )
}
