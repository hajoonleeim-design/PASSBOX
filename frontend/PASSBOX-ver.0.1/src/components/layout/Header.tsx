// 현재 로그인 사용자와 로그아웃 버튼을 보여 주는 상단 공통 영역입니다.
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Button } from '../common/Button'
import { SessionWarning } from '../security/SessionWarning'

export function Header({ isMenuOpen, onMenuToggle }: { isMenuOpen: boolean; onMenuToggle: () => void }) {
  const { session, logout } = useAuth()

  return <header className="header">
    <div className="header__brand">
      <button type="button" className="icon-button header__menu" aria-label={isMenuOpen ? '메뉴 닫기' : '메뉴 열기'} aria-expanded={isMenuOpen} aria-controls="passbox-sidebar" onClick={onMenuToggle}><span aria-hidden="true">☰</span></button>
      <Link to="/" className="header__logo" aria-label="PASSBOX 홈"><img src="/passbox-logo.svg" alt="PASSBOX" /></Link>
      <span className="header__brand-text">공공기관 문서 보안 플랫폼 · {session?.institutionName}</span>
    </div>
    <div className="header__account">
      <div className="header__status">
        <span className="sr-indicator-dot sr-indicator-dot--emerald" />
        <span>보안 시스템 정상 작동 중</span>
      </div>
      <span className="header__user">{session?.displayName} · {session?.role}</span>
      <Link to="/account" className="header__account-link">계정 보안</Link>
      <SessionWarning />
      <Button size="sm" variant="secondary" onClick={() => void logout()}>로그아웃</Button>
    </div>
  </header>
}
