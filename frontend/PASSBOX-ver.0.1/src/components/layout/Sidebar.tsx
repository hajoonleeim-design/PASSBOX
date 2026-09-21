// 서비스의 주요 페이지로 이동하는 좌측 메뉴입니다.
import { NavLink } from 'react-router-dom'
import { PermissionGuard } from '../security/PermissionGuard'

const links = [
  ['/', '홈'],
  ['/upload', '문서 업로드'],
  ['/analysis/recent', '분석'],
  ['/chat', 'AI 대화'],
  ['/support', '사용자 지원'],
  ['/account', '계정 보안'],
] as const

export function Sidebar({ isOpen, onNavigate }: { isOpen: boolean; onNavigate: () => void }) {
  const link = (to: string, label: string) => <NavLink key={to} to={to} end={to === '/'} onClick={onNavigate}><span aria-hidden="true">◈</span>{label}</NavLink>
  return <aside className={`sidebar-shell ${isOpen ? 'sidebar-shell--open' : ''}`}><nav className="sidebar" aria-label="주 메뉴">{links.map(([to, label]) => link(to, label))}<PermissionGuard roles={['APPROVER', 'SECURITY_ADMIN', 'ADMIN']}>{link('/approvals', 'S등급 승인')}</PermissionGuard><PermissionGuard roles={['OPERATOR', 'ADMIN']}>{link('/audit/mock-request', '감사·증적')}</PermissionGuard><PermissionGuard roles={['ADMIN']}>{link('/admin/policy', '관리자 정책')}</PermissionGuard><PermissionGuard roles={['ADMIN']}>{link('/dashboard', '운영 대시보드')}</PermissionGuard></nav></aside>
}
