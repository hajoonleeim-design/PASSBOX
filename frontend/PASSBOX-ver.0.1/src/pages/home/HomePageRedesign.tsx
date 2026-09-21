import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { useAuth } from '../../hooks/useAuth'

type SceneId = 'intake' | 'inference' | 'policy' | 'gateway' | 'audit'

type Scene = {
  id: SceneId
  index: string
  eyebrow: string
  title: string
  emphasis: string
  description: string
  metric: string
  detail: string
}

const scenes: Scene[] = [
  { id: 'intake', index: '01', eyebrow: 'SECURE INTAKE', title: '문서가 들어오는 순간,', emphasis: '보안 경계가 먼저 깨어납니다.', description: '파일은 외부 AI로 이동하기 전에 PASSBOX의 격리 영역으로 들어옵니다. 확장자, MIME, 시그니처, 크기와 무결성을 한 번에 확인합니다.', metric: 'QUARANTINE FIRST', detail: '원문은 검증이 끝날 때까지 외부로 전송되지 않습니다.' },
  { id: 'inference', index: '02', eyebrow: 'LOCAL INTELLIGENCE', title: '문서의 맥락은 먼저', emphasis: '내부 GPU 추론 노드에서 읽습니다.', description: '문서 분류와 위험 신호 탐지는 로컬 모델과 규칙 엔진이 먼저 수행합니다. KoBERT 기반 분류 모델은 원문을 외부로 보내지 않고 C/S/O 후보를 계산합니다.', metric: 'LOCAL MODEL / GPU', detail: '외부 AI는 내부 검사를 통과한 승인 payload만 전달받습니다.' },
  { id: 'policy', index: '03', eyebrow: 'POLICY INTELLIGENCE', title: 'C / S / O 등급은', emphasis: '정책과 담당자가 함께 결정합니다.', description: 'AI 추천은 판단을 돕는 참고자료입니다. 정책 엔진과 담당자의 최종 확인을 거쳐야 다음 단계로 넘어갈 수 있습니다.', metric: 'HUMAN IN THE LOOP', detail: 'C는 차단하고, S는 승인을 요청하며, O는 정책에 따라 진행합니다.' },
  { id: 'gateway', index: '04', eyebrow: 'CONTROLLED GATEWAY', title: '승인된 payload만', emphasis: '통제된 Gateway를 통과합니다.', description: '마스킹과 정책 검사를 통과한 요청만 외부 AI로 전달됩니다. 응답은 다시 PASSBOX로 돌아와 Post-Inspector 검사를 거칩니다.', metric: 'MASK → ALLOW → INSPECT', detail: '전송 전·후 검사가 실패하면 요청은 안전한 오류 상태로 멈춥니다.' },
  { id: 'audit', index: '05', eyebrow: 'EVIDENCE CHAIN', title: '처리의 모든 순간은', emphasis: '감사 증적으로 봉인됩니다.', description: '업로드부터 검사, 분류, 승인, 전송, 응답 검증까지 하나의 타임라인으로 연결합니다. 원문과 AI 응답을 보관하지 않고도 처리 사실을 증명합니다.', metric: 'TRACEABLE BY DEFAULT', detail: '메타데이터 기반 Audit PDF와 Hash Chain으로 사후 검증을 지원합니다.' },
]

function IntakeVisual() {
  return <div className="story-visual__module story-visual__module--intake"><div className="visual-file-card"><span className="visual-file-card__icon">PDF</span><div><strong>confidential.pdf</strong><small>QUARANTINED · 3.2 MB</small></div><span className="visual-file-card__lock">LOCKED</span></div><div className="visual-scan-line" /><div className="visual-scan-status"><span className="signal-dot" /> HASH VERIFIED <strong>SHA-256</strong></div><div className="visual-packet visual-packet--one" /><div className="visual-packet visual-packet--two" /></div>
}

function InferenceVisual() {
  return <div className="story-visual__module story-visual__module--inference"><div className="visual-inference-chip"><div className="visual-chip-core">AI</div><div className="visual-chip-pins visual-chip-pins--top" /><div className="visual-chip-pins visual-chip-pins--bottom" /><strong>LOCAL INFERENCE</strong><small>GPU NODE / PASSBOX-01</small></div><div className="visual-inference-node visual-inference-node--gpu"><span>COMPUTE</span><strong>GPU</strong><small>READY · 72%</small></div><div className="visual-inference-node visual-inference-node--model"><span>MODEL</span><strong>KoBERT</strong><small>CLASSIFIER</small></div><div className="visual-inference-node visual-inference-node--policy"><span>OUTPUT</span><strong>C / S / O</strong><small>REVIEW QUEUE</small></div><div className="visual-inference-lines"><i /><i /><i /></div></div>
}

function PolicyVisual() {
  return <div className="story-visual__module story-visual__module--policy"><div className="visual-radar"><span /><span /><span /><strong>AI</strong></div><div className="visual-grade visual-grade--c"><b>C</b><span>CONFIDENTIAL</span><small>blocked</small></div><div className="visual-grade visual-grade--s"><b>S</b><span>SECURE</span><small>review required</small></div><div className="visual-grade visual-grade--o"><b>O</b><span>OPEN</span><small>policy allowed</small></div></div>
}

function GatewayVisual() {
  return <div className="story-visual__module story-visual__module--gateway"><div className="visual-request"><span>APPROVED PAYLOAD</span><strong>summarize(masked_document)</strong><small>provider: OPENAI · model: gpt-4o-mini</small></div><div className="visual-gate"><span>POLICY GATE</span><strong>ALLOW</strong><small>confirmed grade: O</small></div><div className="visual-route"><i /><i /><i /><b>POST-INSPECTED</b></div><div className="visual-route-tag">TLS 1.3 · MASKED</div></div>
}

function AuditVisual() {
  return <div className="story-visual__module story-visual__module--audit"><div className="visual-audit-header"><span>REQUEST TIMELINE</span><Badge variant="success">SEALED</Badge></div><div className="visual-timeline"><div><i /><span>Document inspected</span><small>09:41:02</small></div><div><i /><span>Grade confirmed · O</span><small>09:41:18</small></div><div><i /><span>Gateway response stored</span><small>09:41:22</small></div><div><i /><span>Audit evidence sealed</span><small>09:41:23</small></div></div><div className="visual-audit-hash"><small>EVIDENCE HASH</small><strong>8f9b...c530dc</strong><span>IMMUTABLE</span></div></div>
}

function SceneVisual({ scene }: { scene: Scene }) {
  return <div className={`story-visual story-visual--${scene.id}`} aria-hidden="true"><div className="story-visual__glow" /><div className="story-visual__topline"><span>PASSBOX CONTROL PLANE</span><b>{scene.index} / {String(scenes.length).padStart(2, '0')}</b></div><div className="story-visual__grid" />{scene.id === 'intake' && <IntakeVisual />}{scene.id === 'inference' && <InferenceVisual />}{scene.id === 'policy' && <PolicyVisual />}{scene.id === 'gateway' && <GatewayVisual />}{scene.id === 'audit' && <AuditVisual />}<div className="story-visual__footer"><span>{scene.metric}</span><i /><small>LIVE SYSTEM</small></div></div>
}

export function HomePageRedesign() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const [activeIndex, setActiveIndex] = useState(0)
  const chapterRefs = useRef<Array<HTMLElement | null>>([])
  const activeScene = scenes[activeIndex]

  useEffect(() => {
    document.documentElement.classList.add('home-scroll-mode')
    return () => document.documentElement.classList.remove('home-scroll-mode')
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (!visible) return
      const index = Number((visible.target as HTMLElement).dataset.sceneIndex)
      if (!Number.isNaN(index)) setActiveIndex(index)
    }, { rootMargin: '-42% 0px -42% 0px', threshold: [0.1, 0.5, 0.9] })
    chapterRefs.current.forEach((chapter) => { if (chapter) observer.observe(chapter) })
    return () => observer.disconnect()
  }, [])

  return <section className="home-page home-story" aria-labelledby="home-title">
    <div className="story-intro"><img className="story-intro__logo" src="/passbox-logo.svg" alt="PASSBOX" /><div className="story-intro__system-line"><span className="signal-dot" /> PASSBOX / N2SF DIGITAL SECURITY SHOWROOM <b>CONTROL PLANE ONLINE</b></div><h1 id="home-title"><span className="story-intro__title-line">AI 업무의 모든 경로를</span><span className="story-intro__title-line story-intro__title-line--accent">보안 가능한 흐름으로.</span></h1><p>문서가 AI로 이동하는 순간을 단순한 전송이 아닌, 검사·분류·승인·증적으로 이어지는 하나의 시스템으로 설계합니다.</p><div className="story-intro__actions"><Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button><Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>안전한 AI 대화</Button></div><div className="story-intro__terminal"><div><span>INPUT</span><strong>PRIVATE DOCUMENT</strong><b>ENCRYPTED</b></div><div><span>LOCAL MODEL</span><strong>GPU / KoBERT</strong><b>READY</b></div><div><span>EXTERNAL AI</span><strong>ALLOWLIST ONLY</strong><b>GATED</b></div></div><div className="story-scroll-hint"><span className="story-scroll-hint__wheel" /><span>스크롤하여 PASSBOX의 보안 흐름 보기</span></div><div className="story-intro__console" aria-hidden="true"><div className="showroom-console__bar"><span>PASSBOX / CONTROL PLANE</span><b><i /> ONLINE</b></div><div className="showroom-console__body"><div className="showroom-console__node showroom-console__node--input"><small>01 · INTAKE</small><strong>PRIVATE DOC</strong><em>QUARANTINED</em></div><div className="showroom-console__connector"><i /><i /><i /></div><div className="showroom-console__node showroom-console__node--model"><small>02 · LOCAL AI</small><strong>GPU / KoBERT</strong><em>INSPECTING</em></div><div className="showroom-console__connector"><i /><i /><i /></div><div className="showroom-console__node showroom-console__node--gate"><small>03 · POLICY GATE</small><strong>C / S / O</strong><em>HUMAN REVIEW</em></div></div><div className="showroom-console__footer"><span>POLICY VERSION</span><strong>LOCAL-TEMPLATE-v1</strong><span>HASH CHAIN</span><b>READY</b></div></div></div>
    <div className="story-progress" aria-label="PASSBOX 보안 흐름 진행 상황">{scenes.map((scene, index) => <button key={scene.id} type="button" className={index === activeIndex ? 'is-active' : ''} onClick={() => chapterRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' })} aria-label={`${scene.index} ${scene.eyebrow}`} aria-current={index === activeIndex ? 'step' : undefined}><span>{scene.index}</span><i /></button>)}</div>
    <div className="story-scroll-shell"><div className="story-visual-column"><SceneVisual scene={activeScene} /></div><div className="story-chapters">{scenes.map((scene, index) => <article key={scene.id} ref={(element) => { chapterRefs.current[index] = element }} data-scene-index={index} className={`story-chapter ${index === activeIndex ? 'is-active' : ''}`}><div className="story-chapter__content"><div className="story-chapter__index"><span>{scene.index}</span><i /></div><p className="eyebrow">{scene.eyebrow}</p><h2>{scene.title}<br /><span>{scene.emphasis}</span></h2><p className="story-chapter__description">{scene.description}</p><div className="story-chapter__meta"><strong>{scene.metric}</strong><span>{scene.detail}</span></div>{index === 0 && <Badge variant="success">LOCAL-TEMPLATE-v1 · ONLINE</Badge>}{index === 1 && <Badge variant="info">PRIVATE INFERENCE · GPU READY</Badge>}{index === scenes.length - 1 && <Button variant="secondary" onClick={() => navigate('/audit/mock-request')}>감사 기록 확인하기</Button>}</div></article>)}</div></div>
    <div className="story-end-grid"><Card><p className="eyebrow">CURRENT SESSION</p><h2>{session?.displayName ?? 'PASSBOX 사용자'}님, 환영합니다.</h2><p>현재 계정은 <strong>{session?.institutionName ?? '테스트 기관'}</strong> · <strong>{session?.role ?? 'USER'}</strong> 권한으로 연결되어 있습니다.</p><div className="security-summary"><div className="security-summary__score">OK</div><div><strong>보안 컨트롤 플레인 정상</strong><br /><small>정책 검사와 감사 기록이 활성화되어 있습니다.</small></div></div></Card><Card><p className="eyebrow">QUICK ACCESS</p><h2>다음 작업을 바로 시작하세요.</h2><p>문서를 분석하거나 승인 대기 중인 요청을 확인할 수 있습니다.</p><div className="form-actions"><Button size="sm" variant="ghost" onClick={() => navigate('/approvals')}>승인 요청 보기</Button><Button size="sm" variant="ghost" onClick={() => navigate('/dashboard')}>운영 대시보드</Button></div></Card></div>
  </section>
}
