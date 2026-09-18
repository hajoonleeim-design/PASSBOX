// 현재 로그인 사용자와 로그아웃 버튼을 보여 주는 상단 공통 영역입니다.
import { useAuth } from '../../hooks/useAuth'
import { Button } from '../common/Button'
import { SessionWarning } from '../security/SessionWarning'

export function Header({ onMenuToggle }: { onMenuToggle: () => void }) {
  const { session, logout } = useAuth()
  return <header className="header"><div className="header__brand"><button type="button" className="icon-button header__menu" aria-label="메뉴 열기" onClick={onMenuToggle}>☰</button><strong>Secure AI Console</strong><span>{session?.institutionName}</span></div><div className="header__account"><span>{session?.displayName} · {session?.role}</span><SessionWarning /><Button size="sm" variant="secondary" onClick={() => void logout()}>로그아웃</Button></div></header>
}
