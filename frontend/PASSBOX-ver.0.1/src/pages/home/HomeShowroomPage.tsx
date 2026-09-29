import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'

const capabilities = [
  ['01', '문서 등록 및 격리 보호', '업로드된 문서는 외부 AI 전송 전 보호 영역에서 접수됩니다. 파일 형식, 크기, 무결성 검증 결과를 확인할 수 있습니다.'],
  ['02', '내부 보안 검사', '내부 보안 엔진과 탐지 규칙이 민감정보, 인증정보, 기밀 신호를 먼저 확인합니다. 검증 전 원문은 외부로 전달하지 않습니다.'],
  ['03', 'C/S/O 등급 판단', '기관 정책과 검토 기준에 따라 요청을 C·S·O 등급으로 분류하고 다음 처리 단계를 결정합니다.'],
  ['04', '마스킹 및 안전 전송', '허용된 요청만 마스킹 또는 토큰화해 승인된 AI 모델로 전달합니다. AI 응답은 공개 전 다시 검사합니다.'],
  ['05', '감사·증적 관리', '문서 접수부터 승인, 전송, 답변 검사까지 Request ID 기반 처리 이력을 안전하게 기록합니다.'],
]

const workflow = [
  ['보호 영역 접수', '문서와 프롬프트는 외부 전송 전에 보호 처리 흐름으로 접수됩니다.'],
  ['보안 검사 및 정책 판단', '내부 검사 결과와 기관 정책 기준으로 C/S/O 등급을 결정합니다.'],
  ['승인된 데이터만 전송', '마스킹·승인·모델 허용 목록을 통과한 요청만 외부 AI에 전달합니다.'],
  ['답변 검증 및 증적 기록', 'Post-Inspector 통과 후 답변을 공개하고 모든 처리 단계를 감사 이력으로 남깁니다.'],
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
    description: 'Job ID를 기준으로 접수, 검사, 파싱, 탐지, 마스킹 등 현재 분석 단계를 확인할 수 있습니다.',
    action: '분석 작업 보기',
    path: '/analysis/recent',
    signal: 'ANALYSIS JOB',
  },
  {
    index: '03',
    title: '결과와 증적을 확인하세요',
    description: 'C/S/O 판정, 승인 상태, Post-Inspector 결과와 처리 이력을 Request ID 기준으로 조회합니다.',
    action: '감사·증적 보기',
    path: '/audit/mock-request',
    signal: 'RESULT & AUDIT',
  },
]

export function HomeShowroomPage() {
  const navigate = useNavigate()

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
            <span><b>01</b> 원문 외부 전송 차단</span>
            <span><b>02</b> C/S/O 정책 기반 판단</span>
            <span><b>03</b> 해시 증적 이력 보관</span>
          </div>
        </div>

        <div className="showroom-visual" aria-label="PASSBOX 보안 처리 흐름">
          <div className="showroom-visual-topbar"><span>PASSBOX SECURITY CONTROL CORE</span><b>PROTECTED FLOW</b></div>
          <div className="showroom-control-board">
            <div className="showroom-control-node showroom-control-node--source"><small>01 / DOCUMENT INTAKE</small><strong>격리 보호</strong><span>서버 검증 대기</span></div>
            <i className="showroom-control-arrow" aria-hidden="true">→</i>
            <div className="showroom-control-node showroom-control-node--engine"><small>02 / LOCAL ENGINE</small><strong>보안 검사</strong><span>원문 외부 미전송</span></div>
            <i className="showroom-control-arrow" aria-hidden="true">→</i>
            <div className="showroom-control-node showroom-control-node--policy"><small>03 / POLICY GATE</small><strong>C · S · O</strong><span>승인 및 정책 판단</span></div>
            <i className="showroom-control-arrow" aria-hidden="true">→</i>
            <div className="showroom-control-node showroom-control-node--result"><small>04 / SAFE RELAY</small><strong>검증 완료</strong><span>Post-Inspector 적용</span></div>
          </div>
          <div className="showroom-control-foot"><span>원문 외부 전송 전 차단</span><span>SHA-256 무결성 확인</span><span>감사 이력 자동 기록</span></div>
        </div>
      </header>

      <section aria-labelledby="showroom-capabilities">
        <div className="showroom-section-heading">
          <div>
            <p className="showroom-section-label">PASSBOX SECURITY FLOW</p>
            <h2 id="showroom-capabilities">문서와 AI 요청을 안전하게 처리하는 과정</h2>
          </div>
          <p>문서 입력부터 AI 응답 공개까지, 보안 상태와 의사결정 근거를 각 단계에서 확인할 수 있습니다.</p>
        </div>
        <div className="showroom-capability-grid">
          {capabilities.map(([index, title, description]) => (
            <Card key={index}>
              <span className="showroom-card-index">{index}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="showroom-operating-model" aria-labelledby="showroom-operating-model">
        <p className="showroom-section-label">HOW PASSBOX PROTECTS</p>
        <h2 id="showroom-operating-model">보안 상태를 확인하면서 업무를 진행합니다.</h2>
        <div className="showroom-workflow">
          {workflow.map(([title, description], index) => (
            <article className="showroom-workflow-item" key={title}>
              <strong>{String(index + 1).padStart(2, '0')}</strong>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
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
          <p>C/S/O 등급은 색상만으로 표시하지 않습니다. 등급 의미와 처리 상태를 함께 표시해 사용자가 다음 조치를 이해할 수 있도록 합니다.</p>
        </div>
        <div className="showroom-grade-list" aria-label="C S O 등급 처리 원칙">
          <div><Badge variant="danger">C등급 · 전송 차단</Badge><span>보안 정책 위반 요청은 외부 AI 전송 전에 중단</span></div>
          <div><Badge variant="warning">S등급 · 승인 필요</Badge><span>권한 있는 담당자의 검토와 승인 후 처리</span></div>
          <div><Badge variant="success">O등급 · 검증 완료</Badge><span>정책 검증을 통과한 요청만 다음 단계로 진행</span></div>
        </div>
      </Card>

      <section className="showroom-footer-panel" aria-labelledby="showroom-next-action">
        <div>
          <p className="showroom-section-label">CONTINUE WITH PASSBOX</p>
          <h2 id="showroom-next-action">최근 처리 현황과 감사 이력을 확인하세요.</h2>
        </div>
        <div className="showroom-footer-cta">
          <Button variant="secondary" onClick={() => navigate('/analysis/recent')}>최근 분석 작업</Button>
          <Button onClick={() => navigate('/audit/mock-request')}>감사·증적 보기</Button>
        </div>
      </section>
    </section>
  )
}
