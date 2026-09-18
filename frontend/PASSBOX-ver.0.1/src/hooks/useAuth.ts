import { useContext } from 'react'
import { AuthContext } from '../stores/AuthContext'

// AuthContext를 편하게 꺼내 쓰기 위한 전용 Hook입니다.
// AuthProvider 밖에서 쓰면 로그인 정보를 알 수 없으므로 명확한 오류를 냅니다.
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider.')
  return context
}
