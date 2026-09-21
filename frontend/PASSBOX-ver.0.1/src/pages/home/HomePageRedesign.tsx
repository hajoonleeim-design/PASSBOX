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
  { id: 'intake', index: '01', eyebrow: '01 · 문서 등록', title: '문서가 들어오면', emphasis: '먼저 안전한 영역에 보관합니다.', description: '파일은 외부 AI로 보내기 전에 PASSBOX의 격리 영역에 저장됩니다. 확장자, 파일 형식, 크기와 무결성을 먼저 확인합니다.', metric: '문서 격리 보관', detail: '검사가 끝날 때까지 원문은 외부로 전송되지 않습니다.' },
  { id: 'inference', index: '02', eyebrow: '02 · 내부 검사', title: '파일 내용은 먼저', emphasis: '내부 검사 서버에서 확인합니다.', description: '내부 분류 모델과 보안 규칙이 문서의 위험 신호를 먼저 확인합니다. 원문을 외부로 보내지 않고 C/S/O 후보 등급을 계산합니다.', metric: '내부 검사 서버 · GPU', detail: '외부 AI에는 내부 검사를 통과한 요청만 전달합니다.' },
  { id: 'policy', index: '03', eyebrow: '03 · 등급 판단', title: 'C/S/O 등급은', emphasis: '정책과 담당자가 함께 결정합니다.', description: '모델의 추천은 판단을 돕는 참고자료입니다. 정책 기준과 담당자의 최종 확인을 거쳐야 다음 단계로 넘어갑니다.', metric: '담당자 최종 확인', detail: 'C는 차단하고, S는 승인을 요청하며, O는 정책에 따라 진행합니다.' },
  { id: 'gateway', index: '04', eyebrow: '04 · 외부 전송', title: '확인된 요청만', emphasis: '외부 AI로 보냅니다.', description: '마스킹과 정책 검사를 통과한 요청만 외부 AI로 전송합니다. 답변은 다시 PASSBOX에서 확인한 뒤 사용자에게 보여줍니다.', metric: '마스킹 → 전송 → 답변 확인', detail: '전송 전·후 검사에 실패하면 요청은 안전하게 중단됩니다.' },
  { id: 'audit', index: '05', eyebrow: '05 · 처리 기록', title: '처리 기록을', emphasis: '나중에도 확인할 수 있게 남깁니다.', description: '업로드부터 검사, 승인, 전송, 답변 확인까지의 처리 이력을 하나의 타임라인으로 남깁니다. 원문과 AI 답변을 보관하지 않고도 처리 사실을 확인할 수 있습니다.', metric: '처리 이력 자동 기록', detail: '메타데이터 기반 보고서와 해시값으로 사후 검증을 지원합니다.' },
]

function IntakeVisual() {
  return <div className="story-visual__module story-visual__module--intake"><div className="visual-file-card"><span className="visual-file-card__icon">PDF</span><div><strong>confidential.pdf</strong><small>격리 보관 · 3.2 MB</small></div><span className="visual-file-card__lock">검사 전</span></div><div className="visual-scan-line" /><div className="visual-scan-status"><span className="signal-dot" /> 파일 무결성 확인 <strong>SHA-256</strong></div><div className="visual-packet visual-packet--one" /><div className="visual-packet visual-packet--two" /></div>
}

function InferenceVisual() {
  return <div className="story-visual__module story-visual__module--inference"><div className="visual-inference-chip"><div className="visual-chip-core">검사</div><div className="visual-chip-pins visual-chip-pins--top" /><div className="visual-chip-pins visual-chip-pins--bottom" /><strong>내부 분류</strong><small>GPU · PASSBOX-01</small></div><div className="visual-inference-node visual-inference-node--gpu"><span>처리 장치</span><strong>GPU</strong><small>준비 완료 · 72%</small></div><div className="visual-inference-node visual-inference-node--model"><span>분류 모델</span><strong>KoBERT</strong><small>문서 분류</small></div><div className="visual-inference-node visual-inference-node--policy"><span>판정 후보</span><strong>C / S / O</strong><small>담당자 확인</small></div><div className="visual-inference-lines"><i /><i /><i /></div></div>
}

function PolicyVisual() {
  return <div className="story-visual__module story-visual__module--policy"><div className="visual-radar"><span /><span /><span /><strong>판정</strong></div><div className="visual-grade visual-grade--c"><b>C</b><span>기밀</span><small>전송 차단</small></div><div className="visual-grade visual-grade--s"><b>S</b><span>민감</span><small>승인 필요</small></div><div className="visual-grade visual-grade--o"><b>O</b><span>공개</span><small>정책 확인 후 전송</small></div></div>
}

function GatewayVisual() {
  return <div className="story-visual__module story-visual__module--gateway"><div className="visual-request"><span>승인된 요청</span><strong>masked_document 요약</strong><small>허용 모델 · gpt-4o-mini</small></div><div className="visual-gate"><span>정책 확인</span><strong>허용</strong><small>확정 등급: O</small></div><div className="visual-route"><i /><i /><i /><b>답변 확인 완료</b></div><div className="visual-route-tag">TLS 1.3 · 마스킹</div></div>
}

function AuditVisual() {
  return <div className="story-visual__module story-visual__module--audit"><div className="visual-audit-header"><span>처리 이력</span><Badge variant="success">기록 완료</Badge></div><div className="visual-timeline"><div><i /><span>문서 검사 완료</span><small>09:41:02</small></div><div><i /><span>등급 확정 · O</span><small>09:41:18</small></div><div><i /><span>AI 답변 수신</span><small>09:41:22</small></div><div><i /><span>처리 기록 저장</span><small>09:41:23</small></div></div><div className="visual-audit-hash"><small>처리 기록 해시</small><strong>8f9b...c530dc</strong><span>변경 감지</span></div></div>
}

function SceneVisual({ scene }: { scene: Scene }) {
  return <div className={`story-visual story-visual--${scene.id}`} aria-hidden="true"><div className="story-visual__glow" /><div className="story-visual__topline"><span>PASSBOX 보안 처리 흐름</span><b>{scene.index} / {String(scenes.length).padStart(2, '0')}</b></div><div className="story-visual__grid" />{scene.id === 'intake' && <IntakeVisual />}{scene.id === 'inference' && <InferenceVisual />}{scene.id === 'policy' && <PolicyVisual />}{scene.id === 'gateway' && <GatewayVisual />}{scene.id === 'audit' && <AuditVisual />}<div className="story-visual__footer"><span>{scene.metric}</span><i /><small>처리 상태</small></div></div>
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
    <div className="story-intro"><div className="story-intro__copy"><img className="story-intro__logo" src="/passbox-logo.svg" alt="PASSBOX" /><div className="story-intro__system-line"><span className="signal-dot" /> PASSBOX / 문서 보안 처리 <b>보안 검사 준비 완료</b></div><h1 id="home-title"><span className="story-intro__title-line">AI 업무에 문서를 넣기 전</span><span className="story-intro__title-line story-intro__title-line--accent">보안부터 확인합니다.</span></h1><p>문서를 외부 AI로 보내기 전에 검사하고, 필요한 경우 승인받고, 처리 이력을 남깁니다.</p><div className="story-intro__actions"><Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button><Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>안전한 AI 대화</Button></div><div className="story-intro__terminal"><div><span>입력</span><strong>업로드 문서</strong><b>격리 보관</b></div><div><span>내부 검사</span><strong>GPU / KoBERT</strong><b>검사 중</b></div><div><span>외부 전송</span><strong>허용된 요청만</strong><b>정책 확인</b></div></div><div className="story-scroll-hint"><span className="story-scroll-hint__wheel" /><span>스크롤하여 PASSBOX의 보안 처리 과정을 확인하세요</span></div></div></div>
    <div className="story-progress" aria-label="PASSBOX 보안 흐름 진행 상황">{scenes.map((scene, index) => <button key={scene.id} type="button" className={index === activeIndex ? 'is-active' : ''} onClick={() => chapterRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' })} aria-label={`${scene.index} ${scene.eyebrow}`} aria-current={index === activeIndex ? 'step' : undefined}><span>{scene.index}</span><i /></button>)}</div>
    <div className="story-scroll-shell"><div className="story-visual-column"><SceneVisual scene={activeScene} /></div><div className="story-chapters">{scenes.map((scene, index) => <article key={scene.id} ref={(element) => { chapterRefs.current[index] = element }} data-scene-index={index} className={`story-chapter ${index === activeIndex ? 'is-active' : ''}`}><div className="story-chapter__content"><div className="story-chapter__index"><span>{scene.index}</span><i /></div><p className="eyebrow">{scene.eyebrow}</p><h2>{scene.title}<br /><span>{scene.emphasis}</span></h2><p className="story-chapter__description">{scene.description}</p><div className="story-chapter__meta"><strong>{scene.metric}</strong><span>{scene.detail}</span></div>{index === 0 && <Badge variant="success">문서 격리 보관 · 확인 전</Badge>}{index === 1 && <Badge variant="info">내부 분류 · GPU 사용</Badge>}{index === scenes.length - 1 && <Button variant="secondary" onClick={() => navigate('/audit/mock-request')}>감사 기록 확인하기</Button>}</div></article>)}</div></div>
    <div className="story-end-grid"><Card><p className="eyebrow">현재 접속 정보</p><h2>{session?.displayName ?? 'PASSBOX 사용자'}님, 환영합니다.</h2><p>현재 계정은 <strong>{session?.institutionName ?? '테스트 기관'}</strong> · <strong>{session?.role ?? 'USER'}</strong> 권한으로 연결되어 있습니다.</p><div className="security-summary"><div className="security-summary__score">정상</div><div><strong>보안 처리 기능이 정상 작동 중입니다.</strong><br /><small>정책 검사와 감사 기록을 사용할 수 있습니다.</small></div></div></Card><Card><p className="eyebrow">바로가기</p><h2>다음 작업을 바로 시작하세요.</h2><p>문서를 분석하거나 승인 대기 중인 요청을 확인할 수 있습니다.</p><div className="form-actions"><Button size="sm" variant="ghost" onClick={() => navigate('/approvals')}>승인 요청 보기</Button><Button size="sm" variant="ghost" onClick={() => navigate('/dashboard')}>운영 대시보드</Button></div></Card></div>
  </section>
}
