import { useEffect, useState, type FormEvent } from 'react'
import { createSensitiveKeyword, deleteSensitiveKeyword, listSensitiveKeywords, updateSensitiveKeyword, type KeywordSeverity, type SensitiveKeyword } from '../../api/sensitiveKeywords'
import { getApiErrorCode } from '../../api/client'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { FormField, SelectInput, TextInput } from '../../components/common/FormControls'
import { ConfirmDialog } from '../../components/common/Modal'

const SEVERITY_LABEL: Record<KeywordSeverity, string> = {
  MEDIUM: '중간 (권장) · 최소 S등급, 승인 후 가려서 전송',
  HIGH: '높음 · 문서 전체 차단, 보안 담당자 검토',
}

function errorMessage(error: unknown): string {
  const code = getApiErrorCode(error)
  if (code === 'FORBIDDEN') return '기밀 키워드를 관리할 권한이 없습니다. (보안 관리자·관리자 전용)'
  if (code === 'HTTP_409') return '이미 등록된 키워드입니다.'
  const message = (error as { message?: string } | null)?.message
  return message || '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

export function SensitiveKeywordsCard() {
  const [rows, setRows] = useState<SensitiveKeyword[] | null>(null)
  const [loadError, setLoadError] = useState('')
  const [keyword, setKeyword] = useState('')
  const [label, setLabel] = useState('')
  const [severity, setSeverity] = useState<KeywordSeverity>('MEDIUM')
  const [formError, setFormError] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<SensitiveKeyword | null>(null)

  useEffect(() => {
    listSensitiveKeywords().then(setRows).catch((error) => setLoadError(errorMessage(error)))
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const trimmed = keyword.trim()
    if (trimmed.replace(/\s/g, '').length < 2) {
      setFormError('키워드는 공백을 제외하고 2자 이상 입력해 주세요.')
      return
    }
    setBusy(true)
    setFormError('')
    try {
      const created = await createSensitiveKeyword({ keyword: trimmed, label: label.trim(), severity })
      setRows((current) => [created, ...(current ?? [])])
      setKeyword('')
      setLabel('')
      setSeverity('MEDIUM')
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function toggle(row: SensitiveKeyword) {
    setActionError('')
    try {
      const updated = await updateSensitiveKeyword(row.id, { enabled: !row.enabled })
      setRows((current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null)
    } catch (error) {
      setActionError(errorMessage(error))
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setBusy(true)
    setActionError('')
    try {
      await deleteSensitiveKeyword(pendingDelete.id)
      setRows((current) => current?.filter((item) => item.id !== pendingDelete.id) ?? null)
      setPendingDelete(null)
    } catch (error) {
      setActionError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="policy-section keyword-card">
      <h2>기밀 키워드 (사내 코드명·은어)</h2>
      <p className="keyword-card__intro">
        내장 탐지 규칙이 알 수 없는 프로젝트 코드명이나 사내 은어를 등록하세요. 등록 즉시 문서 분석, AI 대화, 외부 AI 전송,
        지원 문의 검사에 적용되며, 외부로 나가는 내용에서는 <code>[MASKED:CONFIDENTIAL_KEYWORD]</code>로 가려집니다.
        대·소문자와 띄어쓰기 차이는 무시하며, AI 대화에서는 심각도와 관계없이 전송이 차단됩니다. 변경 이력은 감사 로그에 남고, 키워드 원문 대신 해시만 기록됩니다.
      </p>

      <form className="keyword-card__form" onSubmit={(event) => void submit(event)}>
        <FormField label="키워드" error={formError}>
          <TextInput value={keyword} maxLength={100} placeholder="예: 블루문, Project Atlas" onChange={(event) => { setKeyword(event.target.value); setFormError('') }} />
        </FormField>
        <FormField label="설명 (선택)">
          <TextInput value={label} maxLength={100} placeholder="예: 2026 신규 사업 코드명" onChange={(event) => setLabel(event.target.value)} />
        </FormField>
        <FormField label="심각도">
          <SelectInput value={severity} onChange={(event) => setSeverity(event.target.value as KeywordSeverity)}>
            {(Object.keys(SEVERITY_LABEL) as KeywordSeverity[]).map((value) => <option key={value} value={value}>{SEVERITY_LABEL[value]}</option>)}
          </SelectInput>
        </FormField>
        <Button type="submit" disabled={busy}>{busy ? '처리 중…' : '키워드 등록'}</Button>
      </form>

      {actionError && <Alert variant="danger" title="처리 실패">{actionError}</Alert>}
      {loadError && <Alert variant="danger" title="목록을 불러오지 못했습니다">{loadError}</Alert>}
      {!loadError && rows === null && <p className="keyword-card__note">목록을 불러오는 중입니다…</p>}
      {rows !== null && rows.length === 0 && <p className="keyword-card__note">등록된 기밀 키워드가 없습니다.</p>}
      {rows !== null && rows.length > 0 && (
        <ul className="keyword-card__list">
          {rows.map((row) => (
            <li key={row.id} className={row.enabled ? '' : 'is-disabled'}>
              <div>
                <strong>{row.keyword}</strong>
                <small>{row.label || '설명 없음'} · 심각도 {row.severity}{row.enabled ? '' : ' · 비활성'}</small>
              </div>
              <div className="keyword-card__actions">
                <Button size="sm" variant="secondary" onClick={() => void toggle(row)}>{row.enabled ? '비활성화' : '활성화'}</Button>
                <Button size="sm" variant="ghost" onClick={() => setPendingDelete(row)}>삭제</Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {pendingDelete && (
        <ConfirmDialog
          title="기밀 키워드 삭제"
          message={`'${pendingDelete.keyword}' 키워드를 삭제하면 이후 문서와 AI 요청에서 더 이상 탐지·가림 처리되지 않습니다. 일시적으로 끄려면 '비활성화'를 사용하세요.`}
          confirmLabel="삭제"
          isConfirming={busy}
          onClose={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}
    </Card>
  )
}
