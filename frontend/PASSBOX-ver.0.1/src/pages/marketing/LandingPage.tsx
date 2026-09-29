import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { SplitFlapText } from '../../components/marketing/SplitFlapText'
import { ClearancePassTicket } from '../../components/marketing/ClearancePassTicket'

const FEATURES = [
  { label: 'HWP SANDBOX PARSING', description: '공공 7종 문서 포맷을 격리 환경에서 무해화하며 파싱합니다.' },
  { label: 'PII & SECRET MASKING', description: '주민번호 등 법정 개인정보 7종과 API Key 같은 Secret을 탐지·마스킹합니다.' },
  { label: 'N2SF C/S/O ASSIST', description: '정책 규칙과 AI 모델을 결합해 C·S·O 등급을 자동으로 추천합니다.' },
  { label: 'LOCAL TOKEN VAULT', description: '민감정보를 내부 암호화 토큰으로 치환해 원문을 외부로 보내지 않습니다.' },
  { label: 'PROMPT INJECTION BLOCK', description: '문서와 프롬프트에 숨은 악의적 탈옥 지시문을 원천 차단합니다.' },
  { label: 'POST-INSPECTOR E2E', description: 'AI 응답까지 역방향으로 재검사해 악성 링크·재유출을 막습니다.' },
]

const GENERATIONS = [
  {
    era: 'GEN 1 · 20년 전',
    title: '물리적 망분리',
    description: '인터넷과 업무망을 원천 분단해 생성형 AI 활용이 불가능하고, 업무 혁신이 단절됩니다.',
  },
  {
    era: 'GEN 2 · 5년 전',
    title: '단순 망연계 · 키워드 DLP',
    description: '문맥을 이해하지 못하는 단순 포트 제어 방식이라, 프롬프트 인젝션과 AI 응답 재유출을 막지 못합니다.',
  },
  {
    era: 'GEN 3 · TODAY',
    title: 'PASSBOX N2SF AI Gateway',
    description: '사용자 PC와 외부 AI 사이의 완벽한 샌드박스 에어락. HWP 완벽 파싱, C·S·O 자동 통제, 해시체인 감사 증적까지.',
  },
]

export function LandingPage() {
  const { session } = useAuth()

  return (
    <main className="landing">
      <div className="landing-ticker" role="status" aria-label="시스템 상태 표시줄">
        <span>37.4886° N, 127.0268° E</span>
        <i aria-hidden="true" />
        <span>NIS N2SF PROTOCOL ACTIVE</span>
        <i aria-hidden="true" />
        <span>ZERO TRUST E2E</span>
      </div>

      <header className="landing-nav">
        <span className="landing-nav__brand">PASSBOX</span>
        <nav className="landing-nav__links" aria-label="주 메뉴">
          <a href="#features">핵심 기능</a>
          <a href="#generations">망 보안의 진화</a>
        </nav>
        {session ? (
          <Link to="/home" className="button button--secondary button--md">대시보드로 이동</Link>
        ) : (
          <Link to="/login" className="button button--secondary button--md">로그인</Link>
        )}
      </header>

      <section className="landing-hero">
        <div className="landing-hero__copy">
          <p className="landing-hero__kicker">N2SF MLS · 제로 트러스트 AI 게이트웨이</p>
          <h1>
            공공을 위한<br />
            <em>안전한 AI 관문</em>
          </h1>
          <p className="landing-hero__sub">
            정부 행정망과 외부 생성형 AI를 완벽히 격리하는 국내 유일의 샌드박스 패스박스.
          </p>
          <p className="landing-hero__statement">검증되지 않은 문서는 단 한 글자도 내보내지 않습니다.</p>
          <div className="landing-hero__actions">
            <Link to="/login" className="button button--primary button--lg">지금 시작하기</Link>
            <a href="#features" className="button button--ghost button--lg">핵심 기능 보기</a>
          </div>
        </div>
        <div className="landing-hero__visual">
          <ClearancePassTicket />
        </div>
      </section>

      <section id="features" className="landing-features">
        <p className="landing-section__kicker">CORE MODULES</p>
        <h2>검증되지 않은 문서는 단 한 글자도 나가지 않습니다.</h2>
        <div className="landing-features__grid">
          {FEATURES.map((feature) => (
            <div className="landing-feature-card" key={feature.label}>
              <SplitFlapText text={feature.label} className="landing-feature-card__label" />
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="generations" className="landing-generations">
        <p className="landing-section__kicker">THE EVOLUTION</p>
        <h2>대한민국 망 보안, 3세대에 걸친 진화</h2>
        <div className="landing-generations__grid">
          {GENERATIONS.map((gen, index) => (
            <div className={`landing-generation-card ${index === 2 ? 'is-current' : ''}`} key={gen.era}>
              <span className="landing-generation-card__era">{gen.era}</span>
              <h3>{gen.title}</h3>
              <p>{gen.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-audit">
        <div className="landing-audit__copy">
          <p className="landing-section__kicker">TAMPER-EVIDENT AUDIT</p>
          <h2>원클릭으로 발급되는<br />SHA-256 해시체인 감사 증적</h2>
          <p>
            등급 확정부터 Gateway 전송, 응답 검사까지 모든 처리 이력이 해시체인으로 연결됩니다.
            중간 기록 하나만 조작해도 뒤로 이어지는 모든 해시가 깨져, 위·변조 여부를 즉시 확인할 수 있습니다.
          </p>
        </div>
        <div className="landing-audit__chain" aria-hidden="true">
          <div className="landing-audit__block"><span>등급확정</span><code>a1f9…</code></div>
          <div className="landing-audit__link" />
          <div className="landing-audit__block"><span>Gateway 전송</span><code>c7e2…</code></div>
          <div className="landing-audit__link" />
          <div className="landing-audit__block"><span>응답 검사</span><code>9b04…</code></div>
        </div>
      </section>

      <section className="landing-cta">
        <h2>공공기관을 위한 제로 트러스트,<br />PASSBOX와 함께 시작하세요.</h2>
        <Link to="/login" className="button button--primary button--lg">지금 시작하기</Link>
      </section>

      <footer className="landing-footer">
        <span>PASSBOX · N2SF AI Security Gateway</span>
        <span>한국폴리텍대학 대전캠퍼스 · 클라우드보안과</span>
      </footer>
    </main>
  )
}
