// 세션이 만료되기 전 사용자에게 남은 시간을 알려 주는 경고 컴포넌트입니다.
import { useAuth } from '../../hooks/useAuth'

export function SessionWarning() {
  const { session } = useAuth()
  if (!session) return null
  return <span className="session-status" title={`만료 예정: ${new Date(session.expiresAt).toLocaleString('ko-KR')}`}>세션 정상</span>
}
