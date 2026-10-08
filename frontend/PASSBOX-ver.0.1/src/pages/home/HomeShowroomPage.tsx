import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { HomeStatusSummary } from './HomeStatusSummary'
import { MaskingDemo } from './MaskingDemo'

const capabilities = [
  ['01', '문서 등록 및 격리 보호', '업로드된 문서는 외부 AI 전송 전 보호 영역에서 접수됩니다. 파일 형식, 크기, 무결성 검증 결과를 확인할 수 있습니다.'],
  ['02', '내부 보안 검사', '내부 보안 엔진과 탐지 규칙이 민감정보, 인증정보, 기밀 신호를 먼저 확인합니다. 검증 전 원문은 외부로 전달하지 않습니다.'],
  ['03', 'C/S/O 등급 판단', '문서를 기밀(C)·민감(S)·공개(O) 세 등급으로 나누고, 등급에 따라 외부 AI로 보낼 수 있는지를 결정합니다.'],
  ['04', '마스킹 및 안전 전송', '허용된 요청만 마스킹해 승인된 AI 모델로 전달합니다. AI 응답은 공개 전 다시 검사합니다.'],
  ['05', '감사·증적 관리', '문서 접수부터 승인, 전송, 답변 검사까지 모든 처리 이력을 요청 번호별로 기록하고, 기록이 조작되면 탐지합니다.'],
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
            <span><b>OCR</b> PDF·PPT·워드 속 캡처 이미지 글자까지 검사</span>
            <span><b>변형 탐지</b> ‘공일공’, ‘앳·닷’ 같은 우회 표기도 탐지</span>
            <span><b>SHA-256</b> 처리 기록 조작 여부를 검증 가능</span>
          </div>
        </div>

        <MaskingDemo />
      </header>

      <HomeStatusSummary />

      <section className="home-steps" aria-labelledby="home-steps-title">
        <h2 id="home-steps-title">보안 처리 과정</h2>
        <ol className="home-steps__list">
          {capabilities.map(([index, title, description]) => (
            <li key={index} className="home-steps__item">
              <span className="home-steps__index">{index}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </li>
          ))}
        </ol>
      </section>

      <Card className="showroom-security-card">
        <div>
          <p className="showroom-section-label">보안 등급 안내</p>
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
