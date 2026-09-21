import { useCallback, useEffect, useMemo, useRef, useState, type TouchEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/common/Button'
import { useAuth } from '../../hooks/useAuth'

type SceneId = 'intake' | 'inference' | 'policy' | 'gateway' | 'audit'
type TransitionDirection = 'forward' | 'backward'

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

type ShowroomStage =
  | { kind: 'hero'; key: string }
  | { kind: 'scene'; key: string; scene: Scene }
  | { kind: 'end'; key: string }

const scenes: Scene[] = [
  { id: 'intake', index: '01', eyebrow: '01 · 문서 등록', title: '문서가 들어오면', emphasis: '먼저 안전한 영역에 보관합니다.', description: '파일은 외부 AI로 보내기 전에 PASSBOX의 격리 영역에 저장됩니다. 확장자, 파일 형식, 크기와 무결성을 먼저 확인합니다.', metric: '문서 격리 보관', detail: '검사가 끝날 때까지 원문은 외부로 전송되지 않습니다.' },
  { id: 'inference', index: '02', eyebrow: '02 · 내부 검사', title: '파일 내용은 먼저', emphasis: '내부 검사 서버에서 확인합니다.', description: '내부 분류 모델과 보안 규칙이 문서의 위험 신호를 먼저 확인합니다. 원문을 외부로 보내지 않고 C/S/O 후보 등급을 계산합니다.', metric: '내부 검사 서버 · GPU', detail: '외부 AI에는 내부 검사를 통과한 요청만 전달합니다.' },
  { id: 'policy', index: '03', eyebrow: '03 · 등급 판단', title: 'C/S/O 등급은', emphasis: '정책과 담당자가 함께 결정합니다.', description: '모델의 추천은 판단을 돕는 참고자료입니다. 정책 기준과 담당자의 최종 확인을 거쳐야 다음 단계로 넘어갑니다.', metric: '담당자 최종 확인', detail: 'C는 차단하고, S는 승인을 요청하며, O는 정책에 따라 진행합니다.' },
  { id: 'gateway', index: '04', eyebrow: '04 · 외부 전송', title: '확인된 요청만', emphasis: '외부 AI로 보냅니다.', description: '마스킹과 정책 검사를 통과한 요청만 외부 AI로 전송합니다. 답변은 다시 PASSBOX에서 확인한 뒤 사용자에게 보여줍니다.', metric: '마스킹 → 전송 → 답변 확인', detail: '전송 전·후 검사에 실패하면 요청은 안전하게 중단됩니다.' },
  { id: 'audit', index: '05', eyebrow: '05 · 처리 기록', title: '처리 기록을', emphasis: '나중에도 확인할 수 있게 남깁니다.', description: '업로드부터 검사, 승인, 전송, 답변 확인까지의 처리 이력을 하나의 타임라인으로 남깁니다. 원문과 AI 답변을 보관하지 않고도 처리 사실을 확인할 수 있습니다.', metric: '처리 이력 자동 기록', detail: '메타데이터 기반 보고서와 해시값으로 사후 검증을 지원합니다.' },
]

const totalStages = scenes.length + 2

function IntakeVisual() {
  return <div className="showroom-visual__art showroom-art--intake" aria-hidden="true"><div className="showroom-chamber"><div className="showroom-chamber__rim" /><div className="showroom-file"><span className="showroom-file__type">PDF</span><div><strong>기밀 문서</strong><small>격리 보관 · 3.2 MB</small></div><b>검사 전</b></div><div className="showroom-scan-beam" /><div className="showroom-scan-label"><i /> SHA-256 무결성 확인</div><div className="showroom-chamber__base" /></div><div className="showroom-particle showroom-particle--one" /><div className="showroom-particle showroom-particle--two" /><div className="showroom-particle showroom-particle--three" /></div>
}

function InferenceVisual() {
  return <div className="showroom-visual__art showroom-art--inference" aria-hidden="true"><div className="showroom-core"><div className="showroom-core__ring showroom-core__ring--outer" /><div className="showroom-core__ring showroom-core__ring--inner" /><div className="showroom-core__chip"><strong>검사</strong><small>KoBERT</small></div><div className="showroom-core__beam" /></div><div className="showroom-node showroom-node--gpu"><small>처리 장치</small><strong>GPU CLUSTER</strong><b>준비 완료 · 72%</b></div><div className="showroom-node showroom-node--model"><small>분류 모델</small><strong>KoBERT</strong><b>문서 분류</b></div><div className="showroom-node showroom-node--output"><small>판정 후보</small><strong>C / S / O</strong><b>담당자 확인</b></div><div className="showroom-circuit"><i /><i /><i /><i /></div></div>
}

function PolicyVisual() {
  return <div className="showroom-visual__art showroom-art--policy" aria-hidden="true"><div className="showroom-radar"><div className="showroom-radar__circle showroom-radar__circle--one" /><div className="showroom-radar__circle showroom-radar__circle--two" /><div className="showroom-radar__circle showroom-radar__circle--three" /><div className="showroom-radar__cross showroom-radar__cross--x" /><div className="showroom-radar__cross showroom-radar__cross--y" /><span className="showroom-radar__sweep" /><strong>C/S/O</strong></div><div className="showroom-grade showroom-grade--c"><b>C</b><span>기밀</span><small>전송 차단</small></div><div className="showroom-grade showroom-grade--s"><b>S</b><span>민감</span><small>승인 필요</small></div><div className="showroom-grade showroom-grade--o"><b>O</b><span>공개</span><small>정책 확인 후 전송</small></div></div>
}

function GatewayVisual() {
  return <div className="showroom-visual__art showroom-art--gateway" aria-hidden="true"><div className="showroom-tunnel"><div className="showroom-tunnel__ring showroom-tunnel__ring--one" /><div className="showroom-tunnel__ring showroom-tunnel__ring--two" /><div className="showroom-tunnel__ring showroom-tunnel__ring--three" /><div className="showroom-tunnel__gate"><small>정책 확인</small><strong>허용</strong><b>O 등급</b></div><div className="showroom-packet showroom-packet--one" /><div className="showroom-packet showroom-packet--two" /><div className="showroom-packet showroom-packet--three" /></div><div className="showroom-tunnel-label"><span>TLS 1.3</span><i /> <span>마스킹된 요청만 전송</span></div></div>
}

function AuditVisual() {
  return <div className="showroom-visual__art showroom-art--audit" aria-hidden="true"><div className="showroom-chain"><div className="showroom-chain__line" /><div className="showroom-chain__node showroom-chain__node--one"><b>01</b><span>문서 검사</span><small>09:41:02</small></div><div className="showroom-chain__node showroom-chain__node--two"><b>02</b><span>등급 확정</span><small>09:41:18</small></div><div className="showroom-chain__node showroom-chain__node--three"><b>03</b><span>답변 확인</span><small>09:41:22</small></div><div className="showroom-chain__node showroom-chain__node--four"><b>04</b><span>기록 저장</span><small>09:41:23</small></div></div><div className="showroom-report"><small>감사 기록 보고서</small><strong>처리 이력 확인</strong><b>PDF</b><i /></div><div className="showroom-hash">8f9b...c530dc</div></div>
}

function SceneVisual({ scene }: { scene: Scene }) {
  return <div className={`showroom-visual__frame showroom-visual__frame--${scene.id}`}><div className="showroom-visual__topline"><span>PASSBOX 보안 처리 흐름</span><b>{scene.index} / 05</b></div><div className="showroom-visual__grid" />{scene.id === 'intake' && <IntakeVisual />}{scene.id === 'inference' && <InferenceVisual />}{scene.id === 'policy' && <PolicyVisual />}{scene.id === 'gateway' && <GatewayVisual />}{scene.id === 'audit' && <AuditVisual />}<div className="showroom-visual__footer"><span>{scene.metric}</span><i /><small>보호 상태</small></div></div>
}

function HeroVisual() {
  return <div className="showroom-visual__frame showroom-visual__frame--hero" aria-hidden="true"><div className="showroom-visual__topline"><span>PASSBOX / 문서 보안 처리</span><b>READY</b></div><div className="showroom-hero-orbit"><div className="showroom-hero-orbit__ring showroom-hero-orbit__ring--one" /><div className="showroom-hero-orbit__ring showroom-hero-orbit__ring--two" /><div className="showroom-hero-orbit__ring showroom-hero-orbit__ring--three" /><div className="showroom-hero-orbit__cube"><i /><i /><i /><strong>PB</strong></div><span className="showroom-hero-orbit__dot showroom-hero-orbit__dot--one" /><span className="showroom-hero-orbit__dot showroom-hero-orbit__dot--two" /><span className="showroom-hero-orbit__dot showroom-hero-orbit__dot--three" /></div><div className="showroom-hero-labels"><span><i /> 원문 외부 전송 차단</span><span><i /> 처리 이력 자동 기록</span></div><div className="showroom-visual__footer"><span>문서가 AI로 이동하는 모든 경로</span><i /><small>보안 기준 적용</small></div></div>
}

function EndVisual() {
  return <div className="showroom-visual__frame showroom-visual__frame--end" aria-hidden="true"><div className="showroom-end-orbit"><div className="showroom-end-orbit__ring showroom-end-orbit__ring--one" /><div className="showroom-end-orbit__ring showroom-end-orbit__ring--two" /><div className="showroom-end-orbit__core"><span>PASSBOX</span><strong>증적</strong></div></div><div className="showroom-end-stats"><span><b>01</b> 원문 외부 미보관</span><span><b>02</b> 정책 기반 처리</span><span><b>03</b> 사후 확인 가능</span></div></div>
}

function stageForIndex(index: number): ShowroomStage {
  if (index === 0) return { kind: 'hero', key: 'hero' }
  if (index === totalStages - 1) return { kind: 'end', key: 'end' }
  const scene = scenes[index - 1]
  return { kind: 'scene', key: scene.id, scene }
}

export function HomePageRedesign() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const rootRef = useRef<HTMLElement>(null)
  const touchStartY = useRef<number | null>(null)
  const lockRef = useRef(false)
  const lockTimer = useRef<number | undefined>(undefined)
  const [activeIndex, setActiveIndex] = useState(0)
  const [direction, setDirection] = useState<TransitionDirection>('forward')
  const [isLocked, setIsLocked] = useState(false)
  const stage = useMemo(() => stageForIndex(activeIndex), [activeIndex])

  const moveTo = useCallback((nextIndex: number) => {
    if (lockRef.current) return
    const next = Math.max(0, Math.min(totalStages - 1, nextIndex))
    if (next === activeIndex) return
    lockRef.current = true
    setIsLocked(true)
    setDirection(next > activeIndex ? 'forward' : 'backward')
    setActiveIndex(next)
    lockTimer.current = window.setTimeout(() => {
      lockRef.current = false
      setIsLocked(false)
    }, 850)
  }, [activeIndex])

  const moveBy = useCallback((delta: number) => moveTo(activeIndex + delta), [activeIndex, moveTo])

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    document.documentElement.classList.add('passbox-showroom-mode')

    const onWheel = (event: WheelEvent) => {
      if (Math.abs(event.deltaY) < 4) return
      event.preventDefault()
      moveBy(event.deltaY > 0 ? 1 : -1)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      if (target instanceof HTMLElement && target.closest('input, textarea, select, [contenteditable="true"]')) return
      if (event.key === 'ArrowDown' || event.key === 'PageDown' || event.key === ' ') { event.preventDefault(); moveBy(1) }
      if (event.key === 'ArrowUp' || event.key === 'PageUp') { event.preventDefault(); moveBy(-1) }
      if (event.key === 'Home') { event.preventDefault(); moveTo(0) }
      if (event.key === 'End') { event.preventDefault(); moveTo(totalStages - 1) }
    }

    root.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('keydown', onKeyDown)
    return () => {
      root.removeEventListener('wheel', onWheel)
      window.removeEventListener('keydown', onKeyDown)
      document.documentElement.classList.remove('passbox-showroom-mode')
      if (lockTimer.current) window.clearTimeout(lockTimer.current)
    }
  }, [moveBy, moveTo])

  function onTouchStart(event: TouchEvent<HTMLElement>) {
    touchStartY.current = event.touches[0]?.clientY ?? null
  }

  function onTouchEnd(event: TouchEvent<HTMLElement>) {
    if (touchStartY.current === null) return
    const endY = event.changedTouches[0]?.clientY ?? touchStartY.current
    const distance = touchStartY.current - endY
    touchStartY.current = null
    if (Math.abs(distance) < 48) return
    moveBy(distance > 0 ? 1 : -1)
  }

  return <section ref={rootRef} className={`home-story showroom-shell ${isLocked ? 'is-locked' : ''}`} aria-labelledby="showroom-title" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} tabIndex={-1}>
    <div className="showroom-backdrop" aria-hidden="true"><div className="showroom-backdrop__glow showroom-backdrop__glow--one" /><div className="showroom-backdrop__glow showroom-backdrop__glow--two" /><div className="showroom-backdrop__grid" /></div>
    <div className="showroom-topbar"><div className="showroom-topbar__brand"><img src="/passbox-logo.svg" alt="PASSBOX" /><span>공공의 AI · 안전한 문서 처리</span></div><div className="showroom-topbar__status"><i /> 보안 처리 준비 완료 <b>기관용 환경</b></div></div>
    <div className={`showroom-stage showroom-stage--${stage.kind} showroom-stage--${direction}`} key={stage.key}>
      {stage.kind === 'hero' && <><div className="showroom-copy"><div className="showroom-copy__kicker"><span>PASSBOX</span><b>문서 보안 처리 플랫폼</b></div><div className="showroom-copy__count">INTRO <span>00 / 05</span></div><h1 id="showroom-title">AI 업무에 문서를 넣기 전<br /><em>보안부터 확인합니다.</em></h1><p>문서를 외부 AI로 보내기 전에 검사하고, 필요한 경우 승인받고, 처리 이력을 남깁니다.</p><div className="showroom-copy__actions"><Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button><Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>안전한 AI 대화</Button></div><div className="showroom-specs"><span><b>01</b> 원문 외부 전송 차단</span><span><b>02</b> 정책에 따른 등급 판단</span><span><b>03</b> 처리 이력 보관</span></div></div><div className="showroom-visual"><HeroVisual /></div></>}
      {stage.kind === 'scene' && <><div className="showroom-copy"><div className="showroom-copy__count">{stage.scene.index} <span>/ 05</span></div><div className="showroom-copy__chip">{stage.scene.eyebrow}</div><h1>{stage.scene.title}<br /><em>{stage.scene.emphasis}</em></h1><p>{stage.scene.description}</p><div className="showroom-metric"><strong>{stage.scene.metric}</strong><span>{stage.scene.detail}</span></div>{stage.scene.id === 'audit' && <Button variant="secondary" onClick={() => navigate('/audit/mock-request')}>감사 기록 확인하기</Button>}</div><div className="showroom-visual"><SceneVisual scene={stage.scene} /></div></>}
      {stage.kind === 'end' && <><div className="showroom-copy"><div className="showroom-copy__count">END <span>05 / 05</span></div><div className="showroom-copy__chip">처리 이후까지 확인</div><h1>처리 기록은<br /><em>나중에도 확인할 수 있어야 합니다.</em></h1><p>PASSBOX는 원문을 보관하지 않고도 문서가 어떤 정책을 거쳐 처리되었는지 확인할 수 있도록 기록을 남깁니다.</p><div className="showroom-end-actions"><button type="button" onClick={() => navigate('/upload')}>새 문서 분석 <span>→</span></button><button type="button" onClick={() => navigate('/dashboard')}>운영 현황 보기 <span>→</span></button></div></div><div className="showroom-visual"><EndVisual /></div><div className="showroom-end-session"><span>{session?.displayName ?? 'PASSBOX 사용자'}님</span><b>{session?.institutionName ?? '테스트 기관'} · {session?.role ?? 'USER'}</b></div></>}
    </div>
    <nav className="showroom-indicator" aria-label="보안 처리 단계"><div className="showroom-indicator__line" />{scenes.map((scene, index) => <button key={scene.id} type="button" className={activeIndex === index + 1 ? 'is-active' : ''} onClick={() => moveTo(index + 1)} aria-label={`${scene.index} ${scene.eyebrow}`} aria-current={activeIndex === index + 1 ? 'step' : undefined}><span>{scene.index}</span><i /></button>)}<small>{activeIndex === 0 ? 'INTRO' : activeIndex === totalStages - 1 ? 'END' : `${String(activeIndex).padStart(2, '0')} / 05`}</small></nav>
    <div className="showroom-scroll-hint"><span>{activeIndex === totalStages - 1 ? '위로 스크롤하여 다시 보기' : '스크롤하여 다음 단계 보기'}</span><i /></div>
  </section>
}
