import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { PermissionGuard } from '../security/PermissionGuard'

type SidebarProps = {
  isOpen: boolean
  isCollapsed: boolean
  onNavigate: () => void
}

type IconName = 'home' | 'upload' | 'analysis' | 'chat' | 'approval' | 'audit' | 'policy' | 'dashboard' | 'support' | 'account'

const iconPaths: Record<IconName, string> = {
  home: 'M3 10.5 12 3l9 7.5M5 9v11h14V9M9 20v-6h6v6',
  upload: 'M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4',
  analysis: 'M12 8v4l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  chat: 'M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.5-3A7.5 7.5 0 1 1 20 11.5Z',
  approval: 'm9 12 2 2 4-4m6 2c0 5-3.5 8-9 10-5.5-2-9-5-9-10V6l9-3 9 3v6Z',
  audit: 'M7 3h8l4 4v14H7zM15 3v5h5M10 12h6M10 16h6',
  policy: 'M12 8v4l2.5 1.5M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0ZM19 4l2 2',
  dashboard: 'M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z',
  support: 'M12 17h.01M9.5 9a2.5 2.5 0 1 1 4.2 1.8c-1 .9-1.7 1.3-1.7 2.7M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  account: 'M20 21a8 8 0 0 0-16 0M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
}

function SidebarIcon({ name }: { name: IconName }) {
  return <svg className="sidebar-link__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={iconPaths[name]} /></svg>
}

export function Sidebar({ isOpen, isCollapsed, onNavigate }: SidebarProps) {
  const { pathname } = useLocation()
  const isApprovalRoute = pathname === '/approvals' || pathname.startsWith('/approvals/') || pathname === '/reviews' || pathname.startsWith('/reviews/')
  const [isApprovalOpen, setIsApprovalOpen] = useState(isApprovalRoute)

  useEffect(() => {
    if (isApprovalRoute) setIsApprovalOpen(true)
  }, [isApprovalRoute])

  const link = (to: string, label: string, icon: IconName) => (
    <NavLink key={to} to={to} end={to === '/home'} onClick={onNavigate}>
      <SidebarIcon name={icon} />
      <span className="sidebar-link__label">{label}</span>
    </NavLink>
  )

  const subLink = (to: string, label: string, grade: 'S' | 'C') => (
    <NavLink key={to} to={to} className="sidebar-submenu__link" onClick={onNavigate}>
      <span className={`sidebar-submenu__grade sidebar-submenu__grade--${grade}`} aria-hidden="true">{grade}</span>
      <span>{label}</span>
    </NavLink>
  )

  return (
    <aside
      id="passbox-sidebar"
      className={`sidebar-shell ${isOpen ? 'sidebar-shell--open' : ''} ${isCollapsed ? 'sidebar-shell--collapsed' : ''}`}
    >
      <nav className="sidebar" aria-label="주 메뉴">
        {link('/home', '홈', 'home')}
        {link('/upload', '문서 업로드', 'upload')}
        {link('/analysis/recent', '문서 분석 작업', 'analysis')}
        {link('/chat', '일상 AI 대화', 'chat')}
        <PermissionGuard roles={['APPROVER', 'OPERATOR', 'SECURITY_ADMIN', 'ADMIN']}>
          <div className={`sidebar__group ${isApprovalRoute ? 'sidebar__group--active' : ''}`}>
            <button
              type="button"
              className={`sidebar__group-trigger ${isApprovalOpen ? 'is-open' : ''}`}
              aria-expanded={isApprovalOpen}
              aria-controls="sidebar-approval-pages"
              onClick={() => setIsApprovalOpen((open) => !open)}
            >
              <SidebarIcon name="approval" />
              <span className="sidebar-link__label">승인</span>
              <svg className="sidebar__chevron" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="m4 6 4 4 4-4" /></svg>
            </button>
            <div id="sidebar-approval-pages" className="sidebar-submenu" hidden={!isApprovalOpen}>
              <PermissionGuard roles={['APPROVER', 'SECURITY_ADMIN', 'ADMIN']}>
                {subLink('/approvals', 'S등급 승인', 'S')}
              </PermissionGuard>
              <PermissionGuard roles={['OPERATOR', 'SECURITY_ADMIN', 'ADMIN']}>
                {subLink('/reviews', 'C등급 재검토', 'C')}
              </PermissionGuard>
            </div>
          </div>
        </PermissionGuard>
        <PermissionGuard roles={['OPERATOR', 'ADMIN']}>
          {link('/audit/mock-request', '감사·증적', 'audit')}
        </PermissionGuard>
        <PermissionGuard roles={['ADMIN']}>
          {link('/admin/policy', '관리자 정책', 'policy')}
        </PermissionGuard>
        <PermissionGuard roles={['ADMIN']}>
          {link('/dashboard', '운영 대시보드', 'dashboard')}
        </PermissionGuard>
        {link('/support', '사용자 지원', 'support')}
        {link('/account', '계정 보안', 'account')}
      </nav>
    </aside>
  )
}
