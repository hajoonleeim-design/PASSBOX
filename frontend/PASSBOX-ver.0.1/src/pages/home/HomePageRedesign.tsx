import { useCallback, useEffect, useRef, useState, type TouchEvent } from 'react'
import { useNavigate, type NavigateFunction } from 'react-router-dom'
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
  | { kind: 'hero'; id: 'hero' }
  | { kind: 'scene'; id: SceneId; scene: Scene }
  | { kind: 'end'; id: 'end' }

const WHEEL_THRESHOLD = 5
const TRANSITION_LOCK_MS = 350

const scenes: Scene[] = [
  { id: 'intake', index: '01', eyebrow: '01 · 문서 등록', title: '문서가 들어오면', emphasis: '먼저 안전한 영역에 보관합니다.', description: '파일은 외부 AI로 보내기 전에 PASSBOX의 격리 영역에 저장됩니다. 확장자, 파일 형식, 크기와 무결성을 먼저 확인합니다.', metric: '문서 격리 보관', detail: '검사가 끝날 때까지 원문은 외부로 전송되지 않습니다.' },
  { id: 'inference', index: '02', eyebrow: '02 · 내부 검사', title: '파일 내용은 먼저', emphasis: '내부 검사 서버에서 확인합니다.', description: '내부 분류 모델과 보안 규칙이 문서의 위험 신호를 먼저 확인합니다. 원문을 외부로 보내지 않고 C/S/O 후보 등급을 계산합니다.', metric: '내부 검사 서버 · GPU', detail: '외부 AI에는 내부 검사를 통과한 요청만 전달합니다.' },
  { id: 'policy', index: '03', eyebrow: '03 · 등급 판단', title: 'C/S/O 등급은', emphasis: '정책과 담당자가 함께 결정합니다.', description: '모델의 추천은 판단을 돕는 참고자료입니다. 정책 기준과 담당자의 최종 확인을 거쳐야 다음 단계로 넘어갑니다.', metric: '담당자 최종 확인', detail: 'C는 차단하고, S는 승인을 요청하며, O는 정책에 따라 진행합니다.' },
  { id: 'gateway', index: '04', eyebrow: '04 · 외부 전송', title: '확인된 요청만', emphasis: '외부 AI로 보냅니다.', description: '마스킹과 정책 검사를 통과한 요청만 외부 AI로 전송합니다. 답변은 다시 PASSBOX에서 확인한 뒤 사용자에게 보여줍니다.', metric: '마스킹 → 전송 → 답변 확인', detail: '전송 전·후 검사에 실패하면 요청은 안전하게 중단됩니다.' },
  { id: 'audit', index: '05', eyebrow: '05 · 처리 기록', title: '처리 기록을', emphasis: '나중에도 확인할 수 있게 남깁니다.', description: '업로드부터 검사, 승인, 전송, 답변 확인까지의 처리 이력을 하나의 타임라인으로 남깁니다. 원문과 AI 답변을 보관하지 않고도 처리 사실을 확인할 수 있습니다.', metric: '처리 이력 자동 기록', detail: '메타데이터 기반 보고서와 해시값으로 사후 검증을 지원합니다.' },
]

const showroomStages: ShowroomStage[] = [
  { kind: 'hero', id: 'hero' },
  ...scenes.map((scene): ShowroomStage => ({ kind: 'scene', id: scene.id, scene })),
  { kind: 'end', id: 'end' },
]

function IntakeVisual() {
  return <div className="showroom-visual__art showroom-art--intake hud-console hud-console--vault" aria-hidden="true">
    <div className="hud-console__header"><span>QUARANTINE VAULT / INTAKE-01</span><b className="hud-status hud-status--amber"><i /> 외부 통신 차단</b></div>
    <div className="vault-stage">
      <div className="vault-rail"><span className="is-active">01 <b>REGISTER</b></span><span>02 <b>INSPECT</b></span><span>03 <b>DECIDE</b></span></div>
      <div className="vault-chamber">
        <div className="vault-chamber__label">ISOLATED STORAGE <b>WRITE-ONCE</b></div>
        <div className="vault-document">
          <div className="vault-document__icon"><strong>HWPX</strong><span>DOC</span></div>
          <div className="vault-document__name"><strong>2026_국가보안업무_추진계획.hwpx</strong><small>공공기관 문서 · 3.4 MB · 방금 등록됨</small></div>
          <em>격리 보관 중<small>외부 통신 차단</small></em>
        </div>
        <div className="vault-seal"><i /> QUARANTINED <b>NETWORK OFF</b></div>
        <div className="vault-chamber__grid" />
      </div>
    </div>
    <div className="hud-hashbar"><span>SHA-256 INTEGRITY HASH</span><code>e3b0c44298fc1c149afbf4c8996fb924...</code><b><i /> 검증됨</b></div>
  </div>
}

function InferenceVisual() {
  return <div className="showroom-visual__art showroom-art--inference hud-console hud-console--engine" aria-hidden="true">
    <div className="hud-console__header"><span>INSPECTION ENGINE / LOCAL-02</span><b className="hud-status hud-status--blue"><i /> ON-PREMISE</b></div>
    <div className="engine-status"><strong>PASSBOX On-Premise GPU-01</strong><span>온도 <b>42°C</b></span><span>메모리 <b>18.4 / 24 GB</b></span><em><i /> 연산 준비 완료</em></div>
    <div className="engine-pipeline">
      <div className="engine-node engine-node--source"><small>INPUT</small><strong>문서 텍스트</strong><b>HWPX / 3.4 MB</b></div>
      <i className="engine-arrow">→</i>
      <div className="engine-node engine-node--model"><small>CONTEXT MODEL</small><strong>KoBERT</strong><b>문맥 분류 신경망</b></div>
      <i className="engine-arrow">→</i>
      <div className="engine-node engine-node--pattern"><small>PATTERN SCAN</small><strong>REGEX / SECRET</strong><b>정규식 패턴 분석</b></div>
    </div>
    <div className="engine-metrics">
      <div className="engine-metric"><span>개인정보 7종</span><strong>87%</strong><i><b style={{ width: '87%' }} /></i><small>주민번호 · 계좌 · 연락처</small></div>
      <div className="engine-metric"><span>Secret 탐지</span><strong>64%</strong><i><b style={{ width: '64%' }} /></i><small>API Key · Access Token</small></div>
      <div className="engine-metric"><span>Prompt Injection</span><strong>12%</strong><i><b style={{ width: '12%' }} /></i><small>지시문 패턴 검사</small></div>
    </div>
    <div className="hud-console__footer"><span>SCAN PROFILE <b>PUBLIC-AGENCY / STRICT</b></span><span>LATENCY <b>184 ms</b></span><span className="is-good"><i /> LIVE ANALYSIS</span></div>
  </div>
}

function PolicyVisual() {
  return <div className="showroom-visual__art showroom-art--policy hud-console hud-console--policy" aria-hidden="true">
    <div className="hud-console__header"><span>POLICY DECISION MATRIX / 03</span><b className="hud-status hud-status--blue"><i /> HUMAN REVIEW</b></div>
    <div className="policy-stamp"><i>✓</i><span>기관 정책 엔진 + 담당자 최종 확정</span><b>DECISION READY</b></div>
    <div className="policy-grid">
      <div className="policy-card policy-card--c"><div><b>C</b><span>기밀</span></div><strong>기밀정보·고위험</strong><p>외부 AI 전송 차단<br />내부 격리</p><small>BLOCK / INTERNAL ONLY</small></div>
      <div className="policy-card policy-card--s"><div><b>S</b><span>민감</span></div><strong>개인정보·식별자</strong><p>원문 마스킹 &amp; 토큰화<br />승인 요청</p><small>MASK / APPROVAL REQUIRED</small></div>
      <div className="policy-card policy-card--o"><div><b>O</b><span>공개</span></div><strong>일반 업무정보</strong><p>기관 정책 확인 후<br />전송 허용</p><small>ALLOW / POLICY CHECKED</small></div>
    </div>
    <div className="policy-footer"><span>CLASSIFICATION CONFIDENCE</span><strong>98.2%</strong><i><b /></i><em>담당자 승인 대기</em></div>
  </div>
}

function GatewayVisual() {
  return <div className="showroom-visual__art showroom-art--gateway hud-console hud-console--gateway" aria-hidden="true">
    <div className="hud-console__header"><span>SECURE GATEWAY / OUTBOUND-04</span><b className="hud-status hud-status--green"><i /> TLS 1.3 ACTIVE</b></div>
    <div className="gateway-flow">
      <div className="gateway-node"><small>SOURCE</small><strong>원문 문서</strong><span>국가보안업무.hwpx</span><b className="gateway-node__blocked">원문 외부 미전송</b></div>
      <div className="gateway-stream"><i /><i /><i /><span>검사된 Payload</span></div>
      <div className="gateway-vault"><div><i>PB</i><strong>PASSBOX<br />Token Vault</strong></div><span>원문 난독화<br />식별자 치환</span><b>MASKED</b></div>
      <div className="gateway-stream gateway-stream--out"><i /><i /><i /><span>승인된 Payload</span></div>
      <div className="gateway-node gateway-node--ai"><small>EXTERNAL AI</small><strong>OpenAI / Gemini</strong><span>승인된 모델만 사용</span><b className="gateway-node__allowed">전송 허용</b></div>
    </div>
    <div className="gateway-payload"><span>PAYLOAD PREVIEW</span><code>"요청 내용: [MASKED_USER_01]의 [TOKEN_GOV_DOC] 요약 요청"</code><b><i /> 승인된 Payload만 전송</b></div>
    <div className="hud-console__footer"><span>원문 보관 없음</span><span>정책 게이트 통과</span><span className="is-good"><i /> 암호화 완료</span></div>
  </div>
}

function AuditVisual() {
  return <div className="showroom-visual__art showroom-art--audit hud-console hud-console--audit" aria-hidden="true">
    <div className="hud-console__header"><span>AUDIT EVIDENCE / IMMUTABLE-05</span><b className="hud-status hud-status--green"><i /> HASH VERIFIED</b></div>
    <div className="audit-layout">
      <div className="audit-report">
        <div className="audit-report__top"><span>PDF</span><b>원클릭 PDF</b></div>
        <small>PASSBOX 감사 증적 보고서</small>
        <strong>N2SF-AUDIT-2026-0921</strong>
        <div className="audit-report__rows"><span>문서 처리 이력 <b>05 EVENTS</b></span><span>정책 버전 <b>N2SF-POLICY-1.4</b></span><span>원문 저장 여부 <b>NOT STORED</b></span></div>
        <button type="button"><i>↓</i> PDF 다운로드</button>
      </div>
      <div className="audit-chain">
        <div className="audit-chain__title">APPEND-ONLY HASH CHAIN <b>변경 불가</b></div>
        <div className="audit-chain__line" />
        <div className="audit-chain__event"><i>01</i><span>업로드</span><small>09:41:02</small></div>
        <div className="audit-chain__event"><i>02</i><span>C/S/O 판정</span><small>09:41:18</small></div>
        <div className="audit-chain__event"><i>03</i><span>마스킹 전송</span><small>09:41:22</small></div>
        <div className="audit-chain__event"><i>04</i><span>답변 검증</span><small>09:41:23</small></div>
        <code>8f9b2c71...c530dc</code>
      </div>
    </div>
    <div className="audit-verified"><i>✓</i><span>블록 해시 검증 완료</span><b>APPEND ONLY</b></div>
  </div>
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

function ShowroomStageView({ stage, isActive, direction, session, navigate }: { stage: ShowroomStage; isActive: boolean; direction: TransitionDirection; session: ReturnType<typeof useAuth>['session']; navigate: NavigateFunction }) {
  const disabled = !isActive
  return <div className={`showroom-stage showroom-stage--${stage.kind} showroom-stage--${direction} ${isActive ? 'is-active' : ''}`} data-stage={stage.id} aria-hidden={!isActive}>
    {stage.kind === 'hero' && <><div className="showroom-copy"><div className="showroom-copy__kicker"><span>PASSBOX</span><b>문서 보안 처리 플랫폼</b></div><div className="showroom-copy__count">INTRO <span>00 / 05</span></div><h1>AI 업무에 문서를 넣기 전<br /><em>보안부터 확인합니다.</em></h1><p>문서를 외부 AI로 보내기 전에 검사하고, 필요한 경우 승인받고, 처리 이력을 남깁니다.</p><div className="showroom-copy__actions"><Button size="lg" disabled={disabled} onClick={() => navigate('/upload')}>문서 분석 시작</Button><Button size="lg" variant="secondary" disabled={disabled} onClick={() => navigate('/chat')}>안전한 AI 대화</Button></div><div className="showroom-specs"><span><b>01</b> 원문 외부 전송 차단</span><span><b>02</b> 정책에 따른 등급 판단</span><span><b>03</b> 처리 이력 보관</span></div></div><div className="showroom-visual"><HeroVisual /></div></>}
    {stage.kind === 'scene' && <><div className="showroom-copy"><div className="showroom-copy__count">{stage.scene.index} <span>/ 05</span></div><div className="showroom-copy__chip">{stage.scene.eyebrow}</div><h1>{stage.scene.title}<br /><em>{stage.scene.emphasis}</em></h1><p>{stage.scene.description}</p><div className="showroom-metric"><strong>{stage.scene.metric}</strong><span>{stage.scene.detail}</span></div>{stage.scene.id === 'audit' && <Button variant="secondary" disabled={disabled} onClick={() => navigate('/audit/mock-request')}>감사 기록 확인하기</Button>}</div><div className="showroom-visual"><SceneVisual scene={stage.scene} /></div></>}
    {stage.kind === 'end' && <><div className="showroom-copy"><div className="showroom-copy__count">END <span>05 / 05</span></div><div className="showroom-copy__chip">처리 이후까지 확인</div><h1>처리 기록은<br /><em>나중에도 확인할 수 있어야 합니다.</em></h1><p>PASSBOX는 원문을 보관하지 않고도 문서가 어떤 정책을 거쳐 처리되었는지 확인할 수 있도록 기록을 남깁니다.</p><div className="showroom-end-actions"><button type="button" disabled={disabled} onClick={() => navigate('/upload')}>새 문서 분석 <span>→</span></button><button type="button" disabled={disabled} onClick={() => navigate('/dashboard')}>운영 현황 보기 <span>→</span></button></div></div><div className="showroom-visual"><EndVisual /></div><div className="showroom-end-session"><span>{session?.displayName ?? 'PASSBOX 사용자'}님</span><b>{session?.institutionName ?? '테스트 기관'} · {session?.role ?? 'USER'}</b></div></>}
  </div>
}

export function HomePageRedesign() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const rootRef = useRef<HTMLElement>(null)
  const touchStartY = useRef<number | null>(null)
  const lockRef = useRef(false)
  const lockTimer = useRef<number | undefined>(undefined)
  const activeIndexRef = useRef(0)
  const [activeIndex, setActiveIndex] = useState(0)
  const [direction, setDirection] = useState<TransitionDirection>('forward')
  const [isLocked, setIsLocked] = useState(false)

  const moveTo = useCallback((nextIndex: number) => {
    if (lockRef.current) return
    const currentIndex = activeIndexRef.current
    const next = Math.max(0, Math.min(showroomStages.length - 1, nextIndex))
    if (next === currentIndex) return
    lockRef.current = true
    setIsLocked(true)
    activeIndexRef.current = next
    setDirection(next > currentIndex ? 'forward' : 'backward')
    setActiveIndex(next)
    lockTimer.current = window.setTimeout(() => {
      lockRef.current = false
      setIsLocked(false)
    }, TRANSITION_LOCK_MS)
  }, [])

  const moveBy = useCallback((delta: number) => moveTo(activeIndexRef.current + delta), [moveTo])

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    document.documentElement.classList.add('passbox-showroom-mode')

    const onWheel = (event: WheelEvent) => {
      const normalizedDelta = event.deltaMode === 1 ? event.deltaY * 33 : event.deltaY
      if (Math.abs(normalizedDelta) < WHEEL_THRESHOLD) return
      event.preventDefault()
      moveBy(normalizedDelta > 0 ? 1 : -1)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      if (target instanceof HTMLElement && target.closest('input, textarea, select, [contenteditable="true"]')) return
      if (event.key === 'ArrowDown' || event.key === 'PageDown' || event.key === ' ') { event.preventDefault(); moveBy(1) }
      if (event.key === 'ArrowUp' || event.key === 'PageUp') { event.preventDefault(); moveBy(-1) }
      if (event.key === 'Home') { event.preventDefault(); moveTo(0) }
      if (event.key === 'End') { event.preventDefault(); moveTo(showroomStages.length - 1) }
    }

    window.addEventListener('wheel', onWheel, { capture: true, passive: false })
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('wheel', onWheel, { capture: true })
      window.removeEventListener('keydown', onKeyDown)
      document.documentElement.classList.remove('passbox-showroom-mode')
      if (lockTimer.current !== undefined) window.clearTimeout(lockTimer.current)
      lockTimer.current = undefined
      lockRef.current = false
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

  return <section ref={rootRef} className={`home-story showroom-shell ${isLocked ? 'is-locked' : ''}`} aria-label="PASSBOX 보안 처리 쇼룸" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} tabIndex={-1}>
    <div className="showroom-backdrop" aria-hidden="true"><div className="showroom-backdrop__glow showroom-backdrop__glow--one" /><div className="showroom-backdrop__glow showroom-backdrop__glow--two" /><div className="showroom-backdrop__grid" /></div>
    <div className="showroom-topbar"><div className="showroom-topbar__brand"><img src="/passbox-logo.svg" alt="PASSBOX" /><span>공공의 AI · 안전한 문서 처리</span></div><div className="showroom-topbar__status"><i /> 보안 처리 준비 완료 <b>기관용 환경</b></div></div>
    {showroomStages.map((stage, index) => <ShowroomStageView key={stage.id} stage={stage} isActive={index === activeIndex} direction={direction} session={session} navigate={navigate} />)}
    <nav className="showroom-indicator" aria-label="보안 처리 단계"><div className="showroom-indicator__line" />{scenes.map((scene, index) => <button key={scene.id} type="button" className={activeIndex === index + 1 ? 'is-active' : ''} onClick={() => moveTo(index + 1)} aria-label={`${scene.index} ${scene.eyebrow}`} aria-current={activeIndex === index + 1 ? 'step' : undefined}><span>{scene.index}</span><i /></button>)}<small>{activeIndex === 0 ? 'INTRO' : activeIndex === showroomStages.length - 1 ? 'END' : `${String(activeIndex).padStart(2, '0')} / 05`}</small></nav>
    <div className="showroom-scroll-hint"><span>{activeIndex === showroomStages.length - 1 ? '위로 스크롤하여 다시 보기' : '스크롤하여 다음 단계 보기'}</span><i /></div>
  </section>
}
