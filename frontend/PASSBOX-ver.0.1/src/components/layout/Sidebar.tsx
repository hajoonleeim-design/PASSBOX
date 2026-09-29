import { NavLink } from 'react-router-dom'
import { PermissionGuard } from '../security/PermissionGuard'

type SidebarProps = {
  isOpen: boolean
  isCollapsed: boolean
  onNavigate: () => void
}

export function Sidebar({ isOpen, isCollapsed, onNavigate }: SidebarProps) {
  const link = (to: string, label: string) => (
    <NavLink key={to} to={to} end={to === '/home'} onClick={onNavigate}>
      <span aria-hidden="true">◆</span>
      {label}
    </NavLink>
  )

  return (
    <aside
      id="passbox-sidebar"
      className={`sidebar-shell ${isOpen ? 'sidebar-shell--open' : ''} ${isCollapsed ? 'sidebar-shell--collapsed' : ''}`}
    >
      <nav className="sidebar" aria-label="주 메뉴">
        {link('/home', '홈')}
        {link('/upload', '문서 업로드')}
        {link('/analysis/recent', '문서 분석 작업')}
        {link('/chat', '일상 AI 대화')}
        <PermissionGuard roles={['APPROVER', 'SECURITY_ADMIN', 'ADMIN']}>
          {link('/approvals', 'S등급 승인')}
        </PermissionGuard>
        <PermissionGuard roles={['OPERATOR', 'ADMIN']}>
          {link('/audit/mock-request', '감사·증적')}
        </PermissionGuard>
        <PermissionGuard roles={['ADMIN']}>
          {link('/admin/policy', '관리자 정책')}
        </PermissionGuard>
        <PermissionGuard roles={['ADMIN']}>
          {link('/dashboard', '운영 대시보드')}
        </PermissionGuard>
        {link('/support', '사용자 지원')}
        {link('/account', '계정 보안')}
      </nav>
    </aside>
  )
}
