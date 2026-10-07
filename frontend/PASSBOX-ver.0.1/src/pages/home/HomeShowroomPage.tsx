import { lazy, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { useScrollStages } from '../../hooks/useScrollStages'
import { HomeStatusSummary } from './HomeStatusSummary'

const Passbot3D = lazy(() => import('../../components/marketing/Passbot3D').then((m) => ({ default: m.Passbot3D })))

function hasWebGL() {
  try {
    return Boolean(document.createElement('canvas').getContext('webgl2') ?? document.createElement('canvas').getContext('webgl'))
  } catch {
    return false
  }
}

function PassbotFlat() {
  return (
    <div className="pb-passbot" aria-hidden="true">
      <span className="pb-passbot__glow" />
      <img src="/passbot.png" alt="" />
    </div>
  )
}

const capabilities = [
  ['01', '문서 등록 및 격리 보호', '업로드된 문서는 외부 AI 전송 전 보호 영역에서 접수됩니다. 파일 형식, 크기, 무결성 검증 결과를 확인할 수 있습니다.'],
  ['02', '내부 보안 검사', '내부 보안 엔진과 탐지 규칙이 민감정보, 인증정보, 기밀 신호를 먼저 확인합니다. 검증 전 원문은 외부로 전달하지 않습니다.'],
  ['03', 'C/S/O 등급 판단', '문서를 기밀(C)·민감(S)·공개(O) 세 등급으로 나누고, 등급에 따라 외부 AI로 보낼 수 있는지를 결정합니다.'],
  ['04', '마스킹 및 안전 전송', '허용된 요청만 마스킹해 승인된 AI 모델로 전달합니다. AI 응답은 공개 전 다시 검사합니다.'],
  ['05', '감사·증적 관리', '문서 접수부터 승인, 전송, 답변 검사까지 모든 처리 이력을 요청 번호별로 기록하고, 기록이 조작되면 탐지합니다.'],
]

const onboardingSteps = [
  {
    index: '01',
    title: '문서를 업로드하세요',
    description: '지원 파일을 선택하면 업로드 상태와 서버 검증 상태를 파일별로 확인할 수 있습니다.',
    action: '문서 업로드',
    path: '/upload',
    signal: 'DOCUMENT INTAKE',
  },
  {
    index: '02',
    title: '분석 작업을 확인하세요',
    description: '내 문서가 지금 접수·검사·민감정보 탐지·가림 처리 중 어느 단계에 있는지 확인할 수 있습니다.',
    action: '분석 작업 보기',
    path: '/analysis/recent',
    signal: 'ANALYSIS JOB',
  },
  {
    index: '03',
    title: '결과와 증적을 확인하세요',
    description: '보안 등급 판정, 승인 여부, AI 답변 재검사 결과와 전체 처리 이력을 확인합니다.',
    action: '감사·증적 보기',
    path: '/audit',
    signal: 'RESULT & AUDIT',
  },
]

export function HomeShowroomPage() {
  const navigate = useNavigate()
  const { wrapperRef: flowRef, stage: flowStage, scrollToStage } = useScrollStages<HTMLElement>(capabilities.length)

  return (
    <section className="palantir-showroom" aria-labelledby="showroom-title">
      <header className="showroom-hero-panel">
        <div className="showroom-hero-copy">
          <Badge variant="success">PASSBOX · 공공 문서 보안 플랫폼</Badge>
          <h1 id="showroom-title">
            AI 업무에 문서를 넣기 전
            <br />
            <em>보안부터 확인합니다.</em>
          </h1>
          <p>
            문서를 외부 AI로 전송하기 전에 내부 보안 규칙으로 먼저 검사하고,
            민감한 문서는 담당자의 승인을 거치며, 모든 처리 이력을 투명하게 보관합니다.
          </p>
          <div className="showroom-actions">
            <Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button>
            <Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>일상 AI 대화</Button>
          </div>
          <div className="showroom-hero-specs" aria-label="PASSBOX 핵심 보안 원칙">
            <span><b>OCR</b> PDF·PPT·워드 속 캡처 이미지 글자까지 검사</span>
            <span><b>변형 탐지</b> ‘공일공’, ‘앳·닷’ 같은 우회 표기도 탐지</span>
            <span><b>SHA-256</b> 처리 기록이 조작되면 즉시 탐지</span>
          </div>
        </div>

        <div className="pb-hero-card" aria-label="패스봇이 지키는 3단계 보안 관문">
          <div className="pb-hero-card__bot">
            <span className="pb-hero-card__live"><i aria-hidden="true" />PASSBOX GUARD BOT · 문서 보안 마스코트</span>
            <div className="pb-passbot3d" role="img" aria-label="패스봇 3D 마스코트">
              {hasWebGL() ? (
                <Suspense fallback={<PassbotFlat />}><Passbot3D /></Suspense>
              ) : (
                <PassbotFlat />
              )}
            </div>
          </div>
          <div className="pb-hero-card__caption"><strong>패스봇 · PASSBOT</strong><span>문서가 밖으로 나가기 전, 먼저 지켜봅니다.</span></div>
        </div>
      </header>

      <HomeStatusSummary />

      <section
        id="showroom-capabilities-flow"
        className="home-flow"
        ref={flowRef}
        style={{ height: `${capabilities.length * 55}vh` }}
        aria-labelledby="showroom-capabilities"
      >
        <div className="home-flow__sticky">
          <div className="home-flow__head">
            <p className="showroom-section-label">PASSBOX SECURITY FLOW</p>
            <h2 id="showroom-capabilities">문서와 AI 요청을 안전하게 처리하는 과정</h2>
          </div>
          <div className="home-flow__stage">
            {capabilities.map(([index, title, description], i) => (
              <div key={index} className={`home-flow__panel ${i === flowStage ? 'is-active' : ''}`}>
                <span className="home-flow__index">{index}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
          <div className="home-flow__tabs" role="tablist" aria-label="처리 단계">
            {capabilities.map(([index], i) => (
              <button key={index} type="button" role="tab" aria-selected={i === flowStage} className={i === flowStage ? 'is-active' : ''} onClick={() => scrollToStage(i)}>
                {index}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="showroom-onboarding" aria-labelledby="showroom-onboarding-title">
        <div className="showroom-section-heading">
          <div>
            <p className="showroom-section-label">GET STARTED</p>
            <h2 id="showroom-onboarding-title">PASSBOX를 시작하세요.</h2>
          </div>
          <p>문서 업로드, 분석 진행 확인, 결과와 증적 조회 순서로 보안 처리 흐름을 확인할 수 있습니다.</p>
        </div>
        <ol className="showroom-onboarding-list">
          {onboardingSteps.map((step) => (
            <li className="showroom-onboarding-step" key={step.index}>
              <div className="showroom-onboarding-step__rail" aria-hidden="true"><span>{step.index}</span><i /></div>
              <div className="showroom-onboarding-step__body">
                <p>{step.signal}</p>
                <h3>{step.title}</h3>
                <span>{step.description}</span>
              </div>
              <Button variant="secondary" onClick={() => navigate(step.path)}>{step.action}</Button>
            </li>
          ))}
        </ol>
      </section>

      <Card className="showroom-security-card">
        <div>
          <p className="showroom-section-label">SECURITY DECISION</p>
          <h2>보안 등급에 따라 다음 처리 경로가 달라집니다.</h2>
          <p>문서에 담긴 정보가 얼마나 민감한지에 따라 세 등급으로 나뉘고, 등급마다 외부 AI로 보낼 수 있는지가 달라집니다.</p>
        </div>
        <div className="showroom-grade-list" aria-label="C S O 등급 처리 원칙">
          <div><Badge variant="danger">C 기밀 · 전송 차단</Badge><span>보안 정책 위반 요청은 외부 AI 전송 전에 중단</span></div>
          <div><Badge variant="warning">S 민감 · 승인 필요</Badge><span>권한 있는 담당자의 검토와 승인 후 처리</span></div>
          <div><Badge variant="success">O 공개 · 검증 후 전송</Badge><span>정책 검증을 통과한 요청만 다음 단계로 진행</span></div>
        </div>
      </Card>
    </section>
  )
}
