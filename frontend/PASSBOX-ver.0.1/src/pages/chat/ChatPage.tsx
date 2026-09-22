// AI 요청을 만들고 전송한 뒤 Post-Inspection 결과를 표시하는 화면입니다.
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createChatRequest } from '../../api/aiChat'
import { Alert } from '../../components/common/Alert'
import { Badge, type BadgeVariant } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { FormField, TextareaInput } from '../../components/common/FormControls'
import { ErrorState, LoadingState } from '../../components/common/StateViews'
import { useChatRequest } from '../../hooks/useChatRequest'
import type { AIChatResponse, AIResponseStatus, PayloadStatus, PostInspectionStatus } from '../../types/aiChat'

const payloadLabel: Record<PayloadStatus, string> = { PENDING: '요청 대기', VALIDATING: 'Payload 검증 중', VERIFIED: 'Payload 검증 완료', BLOCKED: 'Payload 차단', FAILED: 'Payload 검증 실패' }
const responseLabel: Record<AIResponseStatus, string> = { NOT_RECEIVED: 'AI 전송 전', RECEIVED: 'AI 응답 수신', POST_INSPECTING: 'Post-Inspector 검증 중', VERIFIED: 'Post-Inspection 검증 완료', BLOCKED: 'AI 응답 차단', FAILED: 'AI 응답 검증 실패', UNKNOWN: '상태 확인 필요' }
const postLabel: Record<PostInspectionStatus, string> = { PENDING: '검증 대기', INSPECTING: '검증 중', VERIFIED: '검증 완료', BLOCKED: '검증 차단', FAILED: '검증 실패', UNKNOWN: '상태 확인 필요' }
const variantFor = (value: string): BadgeVariant => value.includes('차단') || value.includes('실패') ? 'danger' : value.includes('중') || value.includes('대기') ? 'warning' : value.includes('완료') ? 'success' : 'info'
function StatusLine({ label, value }: { label: string; value: string }) { return <div className="chat-status-line"><span>{label}</span><Badge variant={variantFor(value)}>{value}</Badge></div> }
function SecurityNotice({ chat }: { chat: AIChatResponse }) { const post = chat.postInspection; if (post?.status === 'VERIFIED') return <Alert variant="success" title="Post-Inspector 검증 완료">{post.userMessage}</Alert>; if (post?.status === 'BLOCKED') return <Alert variant="danger" title="AI 응답 차단">{post.userMessage}<p>Incident ID: <code>{post.incidentId}</code></p></Alert>; if (post?.status === 'FAILED') return <Alert variant="danger" title="AI 응답 검증 실패">{post.userMessage}<p>Incident ID: <code>{post.incidentId}</code></p></Alert>; if (post?.status === 'INSPECTING') return <Alert variant="warning" title="답변 검증 중">AI 응답을 보안 검증하고 있습니다. 검증 완료 전에는 원문을 표시하지 않습니다.</Alert>; if (chat.decisionStatus === 'BLOCKED') return <Alert variant="danger" title="전송 차단">C등급 요청은 외부 AI 전송이 차단됩니다.</Alert>; if (chat.decisionStatus === 'WAITING_APPROVAL') return <Alert variant="warning" title="승인 필요">S등급 요청은 승인 후 전송할 수 있습니다.</Alert>; if (chat.decisionStatus === 'REJECTED') return <Alert variant="danger" title="전송 불가">반려된 S등급 요청은 전송할 수 없습니다.</Alert>; return <Alert variant="info" title="요청 처리 중">Payload 검증과 AI 응답 보안 검증을 순서대로 진행합니다.</Alert> }

function ChatOverviewNotice() {
  return <div className="chat-overview-notice" aria-label="안전한 AI 대화 안내">
    <div className="chat-overview-notice__heading"><span className="sr-indicator-dot sr-indicator-dot--emerald" />검사된 요청만 외부 AI로 전달됩니다.</div>
    <p>질문은 개인정보·Secret·프롬프트 인젝션 검사를 거친 뒤, 정책을 통과한 Payload만 GPT 또는 Gemini로 전송됩니다. AI 답변도 보안 검증이 완료된 후 표시됩니다.</p>
    <div className="chat-overview-notice__flow" aria-label="AI 대화 보안 처리 흐름"><span>질문 입력</span><i aria-hidden="true">→</i><span>보안검사</span><i aria-hidden="true">→</i><span>마스킹·승인</span><i aria-hidden="true">→</i><span>AI 전송</span><i aria-hidden="true">→</i><span>답변 검증</span></div>
  </div>
}

export function ChatPage() {
  const { requestId } = useParams(); const navigate = useNavigate(); const [prompt, setPrompt] = useState(''); const [submitError, setSubmitError] = useState(''); const [isSubmitting, setIsSubmitting] = useState(false); const { chat, isLoading, errorCode, refresh, retry } = useChatRequest(requestId)
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!prompt.trim()) { setSubmitError('질문을 입력해 주세요.'); return }; setIsSubmitting(true); setSubmitError(''); try { const request = await createChatRequest({ prompt }); setPrompt(''); navigate(`/chat/${request.requestId}`) } catch { setSubmitError('AI 요청을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.') } finally { setIsSubmitting(false) } }
  if (requestId && isLoading && !chat) return <LoadingState label="AI 요청 상태를 불러오는 중입니다." />
  if (requestId && errorCode === 'NOT_FOUND') return <section><h1>AI 요청을 찾을 수 없습니다.</h1><ErrorState label="입력한 Request ID에 해당하는 요청이 없습니다." /><Button onClick={() => navigate('/chat')}>새 대화 시작</Button></section>
  if (requestId && errorCode && !chat) return <section><h1>AI 요청 상태를 확인할 수 없습니다.</h1><ErrorState label="네트워크 연결을 확인한 뒤 다시 시도해 주세요." /><Button onClick={() => void refresh()}>다시 조회</Button></section>
  const responseVisible = chat?.postInspection?.status === 'VERIFIED'
  return <section aria-live="polite"><p className="eyebrow">보안 AI 대화</p><h1>AI 대화</h1><p>Post-Inspector 검증이 완료되기 전에는 AI 응답 원문을 표시하지 않습니다.</p><ChatOverviewNotice />{!requestId && <Card className="chat-card"><Alert variant="info" title="보안 안내">Prompt는 브라우저 저장소에 저장되지 않습니다. 요청은 공통 정책 검증 후 처리됩니다.</Alert><form onSubmit={submit}><FormField label="질문 입력" helpText="민감한 업무 원문은 입력하지 마세요."><TextareaInput rows={7} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="업무 질문을 입력하세요." /></FormField>{submitError && <Alert variant="danger" title="요청 확인 필요">{submitError}</Alert>}<div className="form-actions"><Button type="submit" disabled={isSubmitting}>{isSubmitting ? '요청 생성 중' : '전송'}</Button><Button type="button" variant="ghost" onClick={() => { setPrompt(''); setSubmitError('') }}>입력 취소</Button></div></form></Card>}{chat && <><div className="page-title-row chat-request-title"><div><h2>AI 요청 상태</h2><p>Request ID: <code>{chat.requestId}</code></p></div><Badge variant={variantFor(responseLabel[chat.responseStatus])}>{responseLabel[chat.responseStatus]}</Badge></div>{errorCode && <div className="section-gap"><Alert variant="warning" title="상태 조회 지연">AI 요청 상태를 확인할 수 없습니다. 기존 상태를 유지하고 있습니다.<div className="alert-action"><Button size="sm" variant="secondary" onClick={() => void refresh()}>다시 조회</Button></div></Alert></div>}<div className="chat-status-grid"><Card><h2>요청 및 정책</h2><StatusLine label="Model" value={chat.model} /><StatusLine label="Policy Version" value={chat.policyVersion} /><StatusLine label="Payload" value={payloadLabel[chat.payloadStatus]} /><StatusLine label="판정 상태" value={chat.decisionStatus} /></Card><Card><h2>AI 응답 검증</h2><StatusLine label="AI 전송 상태" value={responseLabel[chat.responseStatus]} /><StatusLine label="Post-Inspector" value={postLabel[chat.postInspection?.status ?? 'PENDING']} /><SecurityNotice chat={chat} /></Card></div>{responseVisible ? <Card className="verified-response"><p className="eyebrow">응답 검증 결과</p><h2>검증된 AI 답변</h2><p>{chat.content}</p></Card> : <Card className="response-withheld"><h2>AI 답변</h2><p>보안 검증이 완료될 때까지 AI 응답 원문을 표시하지 않습니다.</p></Card>}{(chat.responseStatus === 'FAILED' || errorCode) && <div className="job-actions"><Button onClick={() => void retry()}>요청 다시 시도</Button></div>}</>}</section>
}
