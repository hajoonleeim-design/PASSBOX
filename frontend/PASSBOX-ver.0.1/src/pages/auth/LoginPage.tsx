// 아이디와 비밀번호를 받아 로그인하고, 성공하면 원래 가려 했던 화면으로 이동합니다.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import type { ApiError } from '../../api/client'
import { useAuth } from '../../hooks/useAuth'
import '../../styles/login.css'
import '../../styles/login-extra.css'

// 데모 계정 빠른 입력은 개발 서버(npm run dev)에서만 보입니다. 비밀번호는 소스에 두지 않고
// 커밋되지 않는 .env.local 의 VITE_DEMO_PASSWORD 에서만 읽습니다(없으면 아이디만 채움).
const DEMO_ACCOUNTS = [
  { username: 'demo.user', label: '사용자' },
  { username: 'demo.operator', label: '운영자' },
  { username: 'demo.approver', label: '승인자' },
  { username: 'demo.admin', label: '관리자' },
]
const DEMO_PASSWORD = (import.meta.env.VITE_DEMO_PASSWORD as string | undefined) ?? ''
const SHOW_DEMO = import.meta.env.DEV

function CubeMark() {
  return (
    <svg className="ap-mark" viewBox="0 0 100 100" aria-hidden="true">
      <path d="M50 8 88 30 50 52 12 30Z" fill="#3a3a3c" />
      <path d="M12 30 50 52v42L12 72Z" fill="#1d1d1f" />
      <path d="m50 52 38-22v42L50 94Z" fill="#555558" />
    </svg>
  )
}

function EyeIcon({ off }: { off: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
      {off && <path d="m4 4 16 16" />}
    </svg>
  )
}

interface LoginFailure {
  message: string
  lockSeconds?: number
}

// 서버가 준 사유(잘못된 계정·잠금·연결 실패)를 그대로 보여 주어, 사용자가 무엇을 해야 하는지 알 수 있게 합니다.
function describeFailure(reason: unknown): LoginFailure {
  if (reason && typeof reason === 'object') {
    const error = reason as Partial<ApiError>
    if (!error.status) {
      return { message: '서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.' }
    }
    const message = typeof error.message === 'string' && error.message ? error.message : '로그인에 실패했습니다.'
    if (error.status === 429) {
      const minutes = /(\d+)\s*분/.exec(message)
      return { message, lockSeconds: error.retryAfterSeconds ?? (minutes ? Number(minutes[1]) * 60 : 60) }
    }
    return { message }
  }
  return { message: '로그인에 실패했습니다.' }
}

function formatWait(seconds: number): string {
  return seconds >= 120 ? `약 ${Math.ceil(seconds / 60)}분` : `${seconds}초`
}

export function LoginPage() {
  const { login, session } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from
  const usernameRef = useRef<HTMLInputElement>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const [error, setError] = useState('')
  const [lockSeconds, setLockSeconds] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => { usernameRef.current?.focus() }, [])

  useEffect(() => {
    if (lockSeconds <= 0) return
    const timer = window.setInterval(() => setLockSeconds((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [lockSeconds > 0])

  if (session) return <Navigate to={redirectTo ?? '/home'} replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lockSeconds > 0) return
    setError('')
    setIsSubmitting(true)
    try {
      await login({ username, password })
      navigate(redirectTo ?? '/home', { replace: true })
    } catch (reason) {
      const failure = describeFailure(reason)
      setError(failure.message)
      if (failure.lockSeconds) setLockSeconds(failure.lockSeconds)
    } finally {
      setIsSubmitting(false)
    }
  }

  function fillDemo(demoUsername: string) {
    setUsername(demoUsername)
    setPassword(DEMO_PASSWORD)
    setError('')
  }

  const locked = lockSeconds > 0

  return (
    <div className="ap">
      <div className="ap-card">
        <CubeMark />
        <h1 className="ap-title">PASSBOX</h1>
        <p className="ap-sub">공공기관 계정으로 로그인하세요</p>

        {redirectTo && !error && <p className="ap-notice" role="status">로그인이 필요한 화면입니다. 로그인하면 원래 화면으로 이동합니다.</p>}

        <form className="ap-form" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="login-username">아이디</label>
          <input id="login-username" ref={usernameRef} className="ap-input" placeholder="아이디" value={username}
            onChange={(event) => setUsername(event.target.value)} autoComplete="username"
            aria-invalid={Boolean(error)} required />
          <label className="visually-hidden" htmlFor="login-password">비밀번호</label>
          <div className="ap-pw">
            <input id="login-password" className="ap-input" type={showPassword ? 'text' : 'password'} placeholder="비밀번호" value={password}
              onChange={(event) => setPassword(event.target.value)}
              onKeyDown={(event) => setCapsLock(event.getModifierState('CapsLock'))}
              onKeyUp={(event) => setCapsLock(event.getModifierState('CapsLock'))}
              onBlur={() => setCapsLock(false)}
              autoComplete="current-password" aria-invalid={Boolean(error)} required />
            <button type="button" className="ap-eye" onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 표시'} aria-pressed={showPassword}>
              <EyeIcon off={showPassword} />
            </button>
          </div>
          {capsLock && <p className="ap-hint" role="status">Caps Lock이 켜져 있습니다.</p>}
          {error && <p className="ap-error" role="alert">{error}</p>}
          <button type="submit" className="ap-submit" disabled={isSubmitting || locked}>
            {isSubmitting ? '로그인 중…' : locked ? `${formatWait(lockSeconds)} 후 다시 시도` : '로그인'}
          </button>
        </form>

        {SHOW_DEMO && (
          <div className="ap-demo-row" aria-label="데모 계정 빠른 입력">
            <span>데모 계정</span>
            {DEMO_ACCOUNTS.map((account) => (
              <button key={account.username} type="button" className="ap-demo" onClick={() => fillDemo(account.username)} title={account.username}>
                {account.label}
              </button>
            ))}
          </div>
        )}

        <p className="ap-foot">N2SF 기준에 맞춰 설계된 공공기관 전용 게이트웨이</p>
      </div>
    </div>
  )
}
