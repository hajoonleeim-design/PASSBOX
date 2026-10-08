// Warns only when the session is about to expire; stays out of the way otherwise.
import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'

const WARN_BEFORE_MS = 10 * 60 * 1000

export function SessionWarning() {
  const { session } = useAuth()
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  if (!session) return null
  const remaining = new Date(session.expiresAt).getTime() - now
  if (!Number.isFinite(remaining) || remaining > WARN_BEFORE_MS) return null

  const minutes = Math.max(0, Math.ceil(remaining / 60_000))
  return (
    <span className="session-status session-status--warning" role="status" title={`만료 예정: ${new Date(session.expiresAt).toLocaleString('ko-KR')}`}>
      {minutes > 0 ? `세션 ${minutes}분 후 만료` : '세션 만료됨 · 다시 로그인'}
    </span>
  )
}
