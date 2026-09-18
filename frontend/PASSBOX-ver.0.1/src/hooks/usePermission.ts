import { useAuth } from './useAuth'
import type { UserRole } from '../types/auth'

export function usePermission(roles?: UserRole[], permission?: string) {
  const { session } = useAuth()
  if (!session) return false
  return (!roles || roles.includes(session.role)) && (!permission || session.permissions.includes(permission))
}
// 현재 로그인 사용자가 특정 역할을 갖는지 확인하는 간단한 권한 Hook입니다.
