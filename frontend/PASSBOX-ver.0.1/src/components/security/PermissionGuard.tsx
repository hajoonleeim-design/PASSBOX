// 현재 사용자의 역할이 허용 목록에 있을 때만 children을 표시하는 권한용 UI 가드입니다.
// 실제 보안 검증은 반드시 서버에서도 별도로 해야 합니다.
import type { PropsWithChildren, ReactNode } from 'react'
import type { UserRole } from '../../types/auth'
import { usePermission } from '../../hooks/usePermission'

export function PermissionGuard({ children, roles, permission, fallback = null }: PropsWithChildren<{ roles?: UserRole[]; permission?: string; fallback?: ReactNode }>) {
  return usePermission(roles, permission) ? children : fallback
}
