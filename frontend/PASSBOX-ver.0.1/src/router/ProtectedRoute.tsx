import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// 로그인하지 않은 사용자는 로그인 화면으로 보내고,
// 로그인했다면 Outlet 위치에 요청한 하위 화면을 표시합니다.
export function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()
  if (isInitializing) return <p>세션을 확인하는 중입니다...</p>
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />
}
