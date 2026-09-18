// FAQ·연락처 같은 지원 정보를 표시하고 사용자 문의를 접수하는 화면입니다.
import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Alert } from '../../components/common/Alert'
import { Badge, type BadgeVariant } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { FormField, SelectInput, TextInput, TextareaInput } from '../../components/common/FormControls'
import { EmptyState, ErrorState, LoadingState } from '../../components/common/StateViews'
import { useSupport } from '../../hooks/useSupport'
import type { InquiryStatus, SupportCategory, SupportResponse } from '../../types/support'

const categories: { value: SupportCategory; label: string }[] = [
  { value: 'HELP', label: '서비스 이용 도움말' }, { value: 'FILE_FORMAT', label: '파일 형식 문의' }, { value: 'PRIVACY', label: '보안·개인정보 문의' }, { value: 'INQUIRY', label: '일반 문의' }, { value: 'ERROR', label: '오류·장애 문의' }, { value: 'CONTACT', label: '기타 문의' },
]
const statusVariant: Record<InquiryStatus, BadgeVariant> = { RECEIVED: 'info', IN_REVIEW: 'warning', ANSWERED: 'success', CLOSED: 'neutral', FAILED: 'danger' }
const statusLabel: Record<InquiryStatus, string> = { RECEIVED: '접수됨', IN_REVIEW: '검토 중', ANSWERED: '답변 완료', CLOSED: '종료', FAILED: '접수 실패' }
const sensitivePattern = /(password|passwd|token|api[_ -]?key|주민등록|\b\d{6}[- ]?\d{7}\b|\b(?:\d[ -]?){13,19}\b|\b\d{2,4}-\d{2,6}-\d{2,6}\b)/i

export function SupportPage() {
  const { scenario = 'mock-success' } = useParams()
  const { content, isLoading, errorCode, isSubmitting, refresh, submit } = useSupport(scenario)
  const [category, setCategory] = useState<SupportCategory>('HELP')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [response, setResponse] = useState<SupportResponse | null>(null)

  const hasSensitiveWarning = sensitivePattern.test(`${subject}\n${message}`)
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFormError(''); setSubmitError('')
    const trimmedSubject = subject.trim(); const trimmedMessage = message.trim()
    if (!category || !trimmedSubject || !trimmedMessage) { setFormError('분류, 제목, 문의 내용을 모두 입력해 주세요.'); return }
    if (trimmedSubject.length > 120 || trimmedMessage.length > 2_000) { setFormError('제목은 120자, 문의 내용은 2,000자 이내로 입력해 주세요.'); return }
    if (hasSensitiveWarning) { setFormError('민감정보가 포함되었을 가능성이 있습니다. 내용을 제거하거나 마스킹한 뒤 제출해 주세요.'); return }
    try {
      const next = await submit({ category, subject: trimmedSubject, content: trimmedMessage })
      setResponse(next); setSubject(''); setMessage('')
    } catch { setSubmitError('문의 접수에 실패했습니다. 잠시 후 다시 시도해 주세요.') }
  }

  if (isLoading && !content) return <LoadingState label="지원 정보를 불러오는 중입니다." />
  if (errorCode === 'FORBIDDEN') return <section><h1>지원 정보를 조회할 수 없습니다.</h1><ErrorState label="현재 지원 정보에 접근할 권한이 없습니다." /></section>
  if (errorCode === 'NOT_FOUND') return <section><h1>지원 정보를 찾을 수 없습니다.</h1><ErrorState label="요청한 지원 콘텐츠 시나리오가 없습니다." /></section>
  if (errorCode || !content) return <section><h1>지원 정보를 불러오지 못했습니다.</h1><ErrorState label="네트워크 연결을 확인한 뒤 다시 시도해 주세요." /><Button onClick={() => void refresh()}>다시 조회</Button></section>

  const empty = content.help.length === 0 && content.faqs.length === 0 && content.privacy.length === 0
  return <section className="support-page">
    <p className="eyebrow">SUPPORT CENTER</p><h1>사용자 지원</h1><p>서비스 이용 방법과 보안 안내를 확인하고, 필요한 경우 안전한 범위에서 문의를 접수할 수 있습니다.</p>
    {empty ? <Card className="section-gap"><EmptyState label="현재 표시할 지원 콘텐츠가 없습니다." /></Card> : <>
      <Card className="support-section"><h2>도움말</h2><div className="support-help-grid">{content.help.map((item) => <div key={item.id}><strong>{item.title}</strong><p>{item.description}</p></div>)}</div></Card>
      <Card className="support-section"><h2>지원 파일 형식</h2><div className="format-list">{content.fileFormats.map((format) => <Badge key={format} variant="info">{format}</Badge>)}</div><p>파일 크기와 개수 제한은 관리자 및 서버 정책에 따라 달라질 수 있습니다.</p></Card>
      <Card className="support-section"><h2>개인정보·민감정보 보호 안내</h2><div className="privacy-grid">{content.privacy.map((item) => <div key={item.category}><strong>{item.category}</strong><small>대표 예시: {item.example}</small><p>{item.caution}</p></div>)}</div></Card>
      <Card className="support-section"><h2>자주 묻는 질문</h2><div className="faq-list">{content.faqs.map((item) => <details key={item.id}><summary>{item.question}</summary><p>{item.answer}</p></details>)}</div></Card>
    </>}

    <Card className="support-section support-inquiry"><h2>문의 작성</h2><Alert variant="warning" title="민감정보 입력 금지">비밀번호, 인증 토큰, API Key, 원본 문서 내용 또는 개인정보를 문의에 입력하지 마세요. 이 화면의 검사는 경고용 보조 기능이며 실제 보안 탐지 엔진이 아닙니다.</Alert>
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="문의 분류"><SelectInput value={category} onChange={(event) => setCategory(event.target.value as SupportCategory)}>{categories.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</SelectInput></FormField>
        <FormField label="제목" error={formError}><TextInput value={subject} maxLength={120} onChange={(event) => setSubject(event.target.value)} placeholder="문제 상황을 요약해 주세요" /></FormField>
        <FormField label="문의 내용" helpText={`${message.length}/2000자`}><TextareaInput rows={7} value={message} maxLength={2000} onChange={(event) => setMessage(event.target.value)} placeholder="Job ID, Request ID, 발생 시각 등 민감하지 않은 정보를 포함해 주세요." /></FormField>
        {hasSensitiveWarning && <Alert variant="warning" title="민감정보 포함 가능성">문의 내용에 민감정보가 포함되었을 가능성이 있습니다. 비밀번호, 인증 토큰, 원본 문서의 민감정보 등을 제거한 뒤 제출해 주세요.</Alert>}
        {submitError && <Alert variant="danger" title="문의 접수 실패">{submitError}</Alert>}
        <Button type="submit" disabled={isSubmitting || hasSensitiveWarning}>{isSubmitting ? '접수 중' : '문의 접수'}</Button>
      </form>
    </Card>
    {response && <Card className="support-result" aria-live="polite"><h2>문의 접수 결과</h2><Alert variant="success" title="문의가 접수되었습니다.">{response.message}</Alert><dl className="info-list"><div><dt>Inquiry ID</dt><dd><code>{response.inquiryId}</code></dd></div><div><dt>상태</dt><dd><Badge variant={statusVariant[response.status]}><span aria-hidden="true">●</span> {response.status} · {statusLabel[response.status]}</Badge></dd></div><div><dt>접수 시각</dt><dd>{new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(response.receivedAt))}</dd></div></dl></Card>}
  </section>
}
