import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { useAuth } from '../../hooks/useAuth'

type Scene = {
  id: 'perimeter' | 'classify' | 'gateway' | 'audit'
  index: string
  eyebrow: string
  title: string
  emphasis: string
  description: string
  metric: string
  detail: string
}

const scenes: Scene[] = [
  { id: 'perimeter', index: '01', eyebrow: 'SECURE INTAKE', title: 'AI 업무가 시작되는 순간,', emphasis: '보안 경계가 먼저 닫힙니다.', description: '문서와 프롬프트가 외부 모델로 이동하기 전, PASSBOX가 파일을 격리하고 무결성을 확인합니다.', metric: 'PRIVATE BY DEFAULT', detail: '원문은 외부 AI로 전송되지 않습니다.' },
  { id: 'classify', index: '02', eyebrow: 'POLICY INTELLIGENCE', title: '모호한 위험을', emphasis: 'C / S / O 정책으로 바꿉니다.', description: '내부 정책과 문서 문맥을 기준으로 등급을 추천하고, 담당자가 최종 판단을 내립니다.', metric: 'HUMAN IN THE LOOP', detail: 'AI 추천은 참고자료이며 최종 권한은 담당자에게 있습니다.' },
  { id: 'gateway', index: '03', eyebrow: 'CONTROLLED GATEWAY', title: '승인된 요청만', emphasis: '안전한 경로로 통과합니다.', description: '정책 결정 이후에도 전송 전·후 검사를 거쳐 허용된 요청만 Gateway를 통과합니다.', metric: 'POLICY ENFORCED', detail: '차단된 요청은 전송되지 않고 상태로 남습니다.' },
  { id: 'audit', index: '04', eyebrow: 'AUDIT TRAIL', title: '한 번의 요청도', emphasis: '흔적 없이 지나가지 않습니다.', description: '분석, 승인, 전송, 사후 검사까지 모든 단계가 추적 가능한 감사 기록으로 연결됩니다.', metric: 'TRACEABLE END TO END', detail: '감사 증적과 PDF 보고서를 언제든 확인할 수 있습니다.' },
]

function PerimeterVisual() {
  return <div className="story-visual__module story-visual__module--perimeter"><div className="visual-file-card"><span className="visual-file-card__icon">PDF</span><div><strong>confidential.pdf</strong><small>QUARANTINED · 3.2 MB</small></div><span className="visual-file-card__lock">●</span></div><div className="visual-scan-line" /><div className="visual-scan-status"><span className="signal-dot" /> HASH VERIFIED <strong>SHA-256</strong></div></div>
}

function ClassifyVisual() {
  return <div className="story-visual__module story-visual__module--classify"><div className="visual-radar"><span /><span /><span /><strong>AI</strong></div><div className="visual-grade visual-grade--c"><b>C</b><span>CONFIDENTIAL</span><small>restricted</small></div><div className="visual-grade visual-grade--s"><b>S</b><span>SECURE</span><small>review required</small></div><div className="visual-grade visual-grade--o"><b>O</b><span>OPEN</span><small>approved</small></div></div>
}

function GatewayVisual() {
  return <div className="story-visual__module story-visual__module--gateway"><div className="visual-request"><span>AI REQUEST</span><strong>summarize(document)</strong><small>provider: OPENAI · model: gpt-4o-mini</small></div><div className="visual-gate"><span>POLICY GATE</span><strong>ALLOW</strong><small>confirmed grade: C</small></div><div className="visual-route"><i /><i /><i /><b>POST-INSPECTED</b></div></div>
}

function AuditVisual() {
  return <div className="story-visual__module story-visual__module--audit"><div className="visual-audit-header"><span>REQUEST TIMELINE</span><Badge variant="success">COMPLETE</Badge></div><div className="visual-timeline"><div><i /><span>Document inspected</span><small>09:41:02</small></div><div><i /><span>Grade confirmed · C</span><small>09:41:18</small></div><div><i /><span>Gateway response stored</span><small>09:41:22</small></div><div><i /><span>Audit evidence sealed</span><small>09:41:23</small></div></div><div className="visual-audit-hash"><small>EVIDENCE HASH</small><strong>8f9b…6dd3</strong><span>IMMUTABLE</span></div></div>
}

function SceneVisual({ scene }: { scene: Scene }) {
  return <div className={`story-visual story-visual--${scene.id}`} aria-hidden="true"><div className="story-visual__glow" /><div className="story-visual__topline"><span>PASSBOX CONTROL PLANE</span><b>{scene.index} / 04</b></div><div className="story-visual__grid" />{scene.id === 'perimeter' && <PerimeterVisual />}{scene.id === 'classify' && <ClassifyVisual />}{scene.id === 'gateway' && <GatewayVisual />}{scene.id === 'audit' && <AuditVisual />}<div className="story-visual__footer"><span>{scene.metric}</span><i /><small>LIVE SYSTEM</small></div></div>
}

export function HomePageRedesign() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const [activeIndex, setActiveIndex] = useState(0)
  const chapterRefs = useRef<Array<HTMLElement | null>>([])
  const activeScene = scenes[activeIndex]

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
    <div className="story-intro"><img className="story-intro__logo" src="/passbox-logo.svg" alt="PASSBOX" /><p className="eyebrow"><span className="signal-dot" /> PASSBOX / DIGITAL SECURITY SHOWROOM</p><h1 id="home-title"><span className="story-intro__title-line">안전한 AI 업무를 위한</span><span className="story-intro__title-line story-intro__title-line--accent">보안의 새로운 흐름</span></h1><p>문서가 AI로 이동하는 모든 순간을 하나의 보안 여정으로 확인하세요.</p><div className="story-intro__actions"><Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button><Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>안전한 AI 대화</Button></div><div className="story-scroll-hint"><span className="story-scroll-hint__wheel" /><span>스크롤하여 보안 흐름 보기</span></div></div>
    <div className="story-progress" aria-label="보안 여정 진행 상황">{scenes.map((scene, index) => <button key={scene.id} type="button" className={index === activeIndex ? 'is-active' : ''} onClick={() => chapterRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' })} aria-label={`${scene.index} ${scene.eyebrow}`} aria-current={index === activeIndex ? 'step' : undefined}><span>{scene.index}</span><i /></button>)}</div>
    <div className="story-scroll-shell"><div className="story-visual-column"><SceneVisual scene={activeScene} /></div><div className="story-chapters">{scenes.map((scene, index) => <article key={scene.id} ref={(element) => { chapterRefs.current[index] = element }} data-scene-index={index} className={`story-chapter ${index === activeIndex ? 'is-active' : ''}`}><div className="story-chapter__content"><div className="story-chapter__index"><span>{scene.index}</span><i /></div><p className="eyebrow">{scene.eyebrow}</p><h2>{scene.title}<br /><span>{scene.emphasis}</span></h2><p className="story-chapter__description">{scene.description}</p><div className="story-chapter__meta"><strong>{scene.metric}</strong><span>{scene.detail}</span></div>{index === 0 && <Badge variant="success">LOCAL-TEMPLATE-v1 · ONLINE</Badge>}{index === scenes.length - 1 && <Button variant="secondary" onClick={() => navigate('/audit/mock-request')}>감사 기록 확인하기</Button>}</div></article>)}</div></div>
    <div className="story-end-grid"><Card><p className="eyebrow">CURRENT SESSION</p><h2>{session?.displayName ?? 'PASSBOX 사용자'}님, 환영합니다.</h2><p>현재 계정은 <strong>{session?.institutionName ?? '기관'}</strong> · <strong>{session?.role ?? 'USER'}</strong> 권한으로 연결되어 있습니다.</p><div className="security-summary"><div className="security-summary__score">OK</div><div><strong>보안 세션 정상</strong><br /><small>정책 검증과 감사 기록이 활성화되어 있습니다.</small></div></div></Card><Card><p className="eyebrow">QUICK ACCESS</p><h2>다음 작업을 바로 시작하세요.</h2><p>새 문서를 분석하거나 승인 대기 중인 요청을 확인할 수 있습니다.</p><div className="form-actions"><Button size="sm" variant="ghost" onClick={() => navigate('/approvals')}>승인 요청 보기</Button><Button size="sm" variant="ghost" onClick={() => navigate('/dashboard')}>운영 대시보드</Button></div></Card></div>
  </section>
}
