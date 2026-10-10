import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useScrollReveal } from '../../hooks/useScrollReveal'
import { useScrollStages } from '../../hooks/useScrollStages'
import { useActiveSection } from '../../hooks/useActiveSection'
import { ThemeToggle } from '../../components/common/ThemeToggle'
import { ClearancePassTicket } from '../../components/marketing/ClearancePassTicket'
import { CustomCursor } from '../../components/marketing/CustomCursor'
import {
  NetworkLockIcon,
  AlertDocIcon,
  HourglassIcon,
  GradeIcon,
  MaskIcon,
  ChainIcon,
} from '../../components/marketing/LandingIcons'

const TAGS = [
  'HWPX 샌드박스 파싱',
  'PII · Secret 마스킹',
  'N2SF C/S/O 등급분류',
  '되돌릴 수 없는 마스킹',
  '프롬프트 인젝션 차단',
  '해시체인 감사',
]

const WHY_POINTS = [
  {
    icon: NetworkLockIcon,
    title: '망분리 규제의 딜레마',
    body: '내부망과 외부망이 물리적으로 분리된 공공 환경에서는 생성형 AI 활용 자체가 보안 이슈가 됩니다.',
  },
  {
    icon: AlertDocIcon,
    title: '사람의 실수가 만드는 유출 경로',
    body: '담당자의 단순한 복사·붙여넣기 한 번이 민감한 행정 정보를 외부 AI 서비스로 그대로 흘려보낼 수 있습니다.',
  },
  {
    icon: HourglassIcon,
    title: '멈춰선 행정 혁신',
    body: '보안을 이유로 AI 도입을 미루는 사이, 업무 효율화의 기회비용은 계속 쌓여갑니다.',
  },
]

const FEATURES = [
  {
    icon: GradeIcon,
    tag: '01 · CLASSIFICATION',
    label: '등급분류',
    title: 'N2SF C/S/O 등급 자동 분류',
    body: '문서를 업로드하면 국가 정보보안 기준(N2SF)에 따라 기밀(C)·민감(S)·공개(O) 등급을 자동으로 추천합니다.',
  },
  {
    icon: MaskIcon,
    tag: '02 · MASKING',
    label: '마스킹',
    title: '외부 전송 전 민감 정보 자동 가림',
    body: '개인정보와 Secret은 외부로 나가기 전 [MASKED:유형]으로 치환됩니다. 외부로 나간 내용에는 가려진 원문이 남지 않아 되돌릴 수 없습니다.',
  },
  {
    icon: ChainIcon,
    tag: '03 · AUDIT LOG',
    label: '해시체인',
    title: '위·변조를 검증하는 해시체인 감사 로그',
    body: '모든 처리 이력이 해시체인으로 연결되어, 로그가 사후에 한 건이라도 조작되면 검증 시 바로 드러납니다.',
  },
]

const DOCK_ITEMS = [
  { id: 'hero', label: 'HOME' },
  { id: 'why', label: 'WHY' },
  { id: 'features', label: 'FEATURES' },
  { id: 'start', label: 'START' },
]

export function LandingPage() {
  const { session } = useAuth()
  const [scrolled, setScrolled] = useState(false)
  const revealRef = useScrollReveal<HTMLDivElement>()
  const { wrapperRef: flowRef, stage: flowStage, scrollToStage: scrollToFlowStage } = useScrollStages<HTMLDivElement>(FEATURES.length)
  const activeSection = useActiveSection(DOCK_ITEMS.map((item) => item.id))

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // 에스원 쇼룸처럼 이 페이지에 있는 동안은 브라우저 기본 스크롤바를 숨기고,
  // 대신 하단 독(dock) 내비게이션으로 현재 위치를 보여줍니다.
  useEffect(() => {
    document.documentElement.classList.add('hide-native-scrollbar')
    return () => document.documentElement.classList.remove('hide-native-scrollbar')
  }, [])

  return (
    <div ref={revealRef} className="landing">
      <CustomCursor />
      <header className={`landing-nav ${scrolled ? 'is-scrolled' : ''}`}>
        <Link to="/" className="landing-nav__brand"><img src="/passbox-logo.svg" alt="PASSBOX" /></Link>
        <nav className="landing-nav__links" aria-label="주 메뉴">
          <a href="#features">핵심 기능</a>
          <a href="#why">도입 배경</a>
        </nav>
        <ThemeToggle className="landing-nav__theme" />
        {session ? (
          <Link to="/home" className="landing-nav__cta">대시보드로 이동</Link>
        ) : (
          <Link to="/login" className="landing-nav__cta">로그인</Link>
        )}
      </header>

      <section id="hero" className="landing-hero">
        <div className="landing-hero__grid" aria-hidden="true" />

        <div className="landing-hero__inner">
          <div className="landing-hero__copy reveal">
            <p className="landing-hero__kicker">N2SF MLS · ZERO TRUST AI GATEWAY</p>
            <h1>
              공공기관 AI 도입의 새로운 표준,
              <br />
              <em>PASSBOX</em>
            </h1>
            <p className="landing-hero__sub">
              망분리 환경에서도 안전하게. 검증을 통과하지 못한 문서는 외부로
              나가지 않는, 공공기관 전용 AI 보안 게이트웨이.
            </p>
            <div className="landing-hero__actions">
              <Link to="/login" className="button button--primary button--lg">지금 시작하기</Link>
              <a href="#features" className="button button--ghost button--lg">핵심 기능 보기</a>
            </div>
          </div>

          <div className="landing-hero__visual reveal" style={{ transitionDelay: '120ms' }}>
            <ClearancePassTicket />
          </div>
        </div>

        <a href="#tags" className="landing-hero__scroll-cue">
          <span>스크롤하여 더 보기</span>
          <i aria-hidden="true" />
        </a>
      </section>

      <section id="tags" className="landing-tags reveal">
        <span className="landing-tags__label">핵심 모듈</span>
        <div className="landing-tags__row">
          {TAGS.map((tag) => (
            <span key={tag} className="landing-tag">{tag}</span>
          ))}
        </div>
        <a href="#features" className="landing-tags__all">전체보기 →</a>
      </section>

      <section id="why" className="landing-why">
        <div className="landing-section__head reveal">
          <p className="landing-section__kicker">WHY PASSBOX</p>
          <h2>왜 공공기관에는 별도의 AI 게이트웨이가 필요한가</h2>
        </div>

        <div className="landing-why__grid">
          {WHY_POINTS.map((point, i) => (
            <div key={point.title} className="landing-why-card reveal" style={{ transitionDelay: `${i * 100}ms` }}>
              <div className="landing-why-card__icon"><point.icon className="landing-icon" /></div>
              <h3>{point.title}</h3>
              <p>{point.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section
        id="features"
        className="landing-flow"
        ref={flowRef}
        style={{ height: `${FEATURES.length * 100}vh` }}
      >
        <div className="landing-flow__sticky">
          <div className="landing-flow__head reveal">
            <p className="landing-section__kicker">CORE FEATURES</p>
            <h2>PASSBOX 핵심 아키텍처</h2>
          </div>

          <div className="landing-flow__stage">
            {FEATURES.map((feature, i) => (
              <div key={feature.title} className={`landing-flow__panel ${i === flowStage ? 'is-active' : ''}`}>
                <div className="landing-flow__icon"><feature.icon className="landing-icon" /></div>
                <span className="landing-flow__tag">{feature.tag}</span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </div>
            ))}
          </div>

          <div className="landing-flow__tabs" role="tablist" aria-label="PASSBOX 핵심 기능 단계">
            {FEATURES.map((feature, i) => (
              <button
                key={feature.label}
                type="button"
                role="tab"
                aria-selected={i === flowStage}
                className={i === flowStage ? 'is-active' : ''}
                onClick={() => scrollToFlowStage(i)}
              >
                {feature.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section id="start" className="landing-cta">
        <div className="reveal">
          <h2>공공기관을 위한 제로 트러스트,<br />PASSBOX와 함께 시작하세요.</h2>
          <Link to="/login" className="button button--primary button--lg">지금 시작하기</Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer__brand">
          <img src="/passbox-logo.svg" alt="PASSBOX" className="landing-footer__logo" />
          <p>공공기관 전용 제로 트러스트 AI 게이트웨이. N2SF 기준 기반의 데이터 분류와 마스킹으로 안전한 AI 활용을 지원합니다.</p>
        </div>

        <div className="landing-footer__col">
          <h4>제품</h4>
          <a href="#features">핵심 기능</a>
          <a href="#why">도입 배경</a>
        </div>

        <div className="landing-footer__col">
          <h4>도입 문의</h4>
          <Link to="/login">로그인 · 문의하기</Link>
          <span>평일 09:00 – 18:00</span>
        </div>

        <div className="landing-footer__col">
          <h4>만든 곳</h4>
          <span>한국폴리텍대학 대전캠퍼스</span>
          <span>클라우드보안과</span>
        </div>

        <div className="landing-footer__bottom">
          <span>© {new Date().getFullYear()} PASSBOX · N2SF AI Security Gateway</span>
        </div>
      </footer>

      <nav className="landing-dock" aria-label="페이지 섹션 이동">
        {DOCK_ITEMS.map((item) => (
          <a key={item.id} href={`#${item.id}`} className={activeSection === item.id ? 'is-active' : ''}>
            {item.label}
          </a>
        ))}
      </nav>
    </div>
  )
}
