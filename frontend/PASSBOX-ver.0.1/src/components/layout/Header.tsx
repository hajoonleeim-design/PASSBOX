// 현재 로그인 사용자와 로그아웃 버튼을 보여 주는 상단 공통 영역입니다.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Button } from '../common/Button'
import { Modal } from '../common/Modal'
import { SessionWarning } from '../security/SessionWarning'

const DEMO_CHECKS = [
  { name: 'API 게이트웨이', detail: '요청 수신 및 응답', state: '정상' },
  { name: '문서 검증 파이프라인', detail: '파일 형식·무결성 검사', state: '정상' },
  { name: '보안 정책 엔진', detail: '정책 데모 v1.4 적용', state: '정상' },
  { name: '감사 증적 저장', detail: '샘플 이벤트 체인', state: '정상' },
]

export function Header({ isMenuOpen, onMenuToggle }: { isMenuOpen: boolean; onMenuToggle: () => void }) {
  const { session, logout } = useAuth()
  const [isStatusOpen, setIsStatusOpen] = useState(false)
  const [isDemoChecking, setIsDemoChecking] = useState(false)
  const [demoRunCount, setDemoRunCount] = useState(0)
  const demoCheckTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (demoCheckTimer.current !== null) window.clearTimeout(demoCheckTimer.current)
  }, [])

  function runDemoCheck() {
    if (isDemoChecking) return
    setIsDemoChecking(true)
    demoCheckTimer.current = window.setTimeout(() => {
      setDemoRunCount((count) => count + 1)
      setIsDemoChecking(false)
      demoCheckTimer.current = null
    }, 900)
  }

  return <header className="header">
    <div className="header__brand">
      <button type="button" className="icon-button header__menu" aria-label={isMenuOpen ? '메뉴 닫기' : '메뉴 열기'} aria-expanded={isMenuOpen} aria-controls="passbox-sidebar" onClick={onMenuToggle}><span aria-hidden="true">☰</span></button>
      <Link to="/home" className="header__logo" aria-label="PASSBOX 홈"><img src="/passbox-logo.svg" alt="PASSBOX" /></Link>
      <span className="header__brand-text">공공기관 문서 보안 플랫폼 · {session?.institutionName}</span>
    </div>
    <div className="header__account">
      <button type="button" className="header__status" aria-haspopup="dialog" aria-expanded={isStatusOpen} onClick={() => setIsStatusOpen(true)}>
        <span className="sr-indicator-dot sr-indicator-dot--emerald" />
        <span>보안 시스템 정상 작동 중</span>
        <span className="header__status-chevron" aria-hidden="true">⌄</span>
      </button>
      <span className="header__user">{session?.displayName} · {session?.role}</span>
      <Link to="/account" className="header__account-link">계정 보안</Link>
      <SessionWarning />
      <Button size="sm" variant="secondary" onClick={() => void logout()}>로그아웃</Button>
    </div>
    {isStatusOpen && <Modal title="보안 시스템 운영 상태" onClose={() => setIsStatusOpen(false)}>
      <div className="security-status-demo">
        <div className="security-status-demo__notice">
          <span className="security-status-demo__demo-label">데모 데이터</span>
          <p>아래 상태와 증적은 화면 시연용 예시이며 실제 서버 점검 결과가 아닙니다.</p>
        </div>
        <div className="security-status-demo__summary">
          <span className="security-status-demo__summary-icon" aria-hidden="true">✓</span>
          <div><strong>{isDemoChecking ? '샘플 점검을 진행하고 있습니다' : '모든 샘플 점검 항목이 정상입니다'}</strong><small>PASSBOX 보안 운영 상태 · 데모 시나리오</small></div>
        </div>
        <ul className="security-status-demo__checks" aria-label="데모 점검 항목">
          {DEMO_CHECKS.map((check) => <li key={check.name}>
            <span className="security-status-demo__check-icon" aria-hidden="true">✓</span>
            <span className="security-status-demo__check-copy"><strong>{check.name}</strong><small>{check.detail}</small></span>
            <span className="security-status-demo__check-state">{isDemoChecking ? '확인 중' : check.state}</span>
          </li>)}
        </ul>
        <div className="security-status-demo__evidence">
          <div><span>샘플 증적 ID</span><code>DEMO-EVT-{String(240 + demoRunCount).padStart(4, '0')}</code></div>
          <div><span>최근 조치 예시</span><strong>{isDemoChecking ? '점검 이벤트 기록 중' : '정책 버전 확인 완료'}</strong></div>
          <small>실제 감사 로그나 운영 조치는 생성되지 않습니다.</small>
        </div>
        <div className="security-status-demo__actions">
          <small>{demoRunCount > 0 ? `샘플 점검 ${demoRunCount}회 실행됨` : '실제 서비스에 요청을 보내지 않습니다.'}</small>
          <Button type="button" variant="secondary" onClick={runDemoCheck} disabled={isDemoChecking}>
            {isDemoChecking ? '샘플 점검 중…' : '샘플 점검 다시 실행'}
          </Button>
        </div>
      </div>
    </Modal>}
  </header>
}
