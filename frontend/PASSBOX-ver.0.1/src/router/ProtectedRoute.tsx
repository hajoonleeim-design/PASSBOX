import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { wasJustLoggedOut } from '../stores/logoutMarker'

// 로그인하지 않은 사용자는 로그인 화면으로 보내고,
// 로그인했다면 Outlet 위치에 요청한 하위 화면을 표시합니다.
export function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()
  if (isInitializing) return <p>세션을 확인하는 중입니다...</p>
  if (isAuthenticated) return <Outlet />
  // 사용자가 직접 로그아웃한 경우에는 "로그인이 필요한 화면" 안내와 원래 화면 복귀를 붙이지 않는다
  return <Navigate to="/login" replace state={wasJustLoggedOut() ? undefined : { from: location.pathname }} />
}
