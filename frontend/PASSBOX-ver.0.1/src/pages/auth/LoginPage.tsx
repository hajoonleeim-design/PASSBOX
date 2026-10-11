// 아이디와 비밀번호를 받아 로그인하고, 성공하면 원래 가려 했던 화면으로 이동합니다.
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import '../../styles/login.css'

// 데모 계정 자동 입력은 개발 서버(npm run dev)에서만 보입니다. 비밀번호는 소스에 두지 않고
// 커밋되지 않는 .env.local 의 VITE_DEMO_PASSWORD 에서만 읽습니다(없으면 아이디만 채움).
const DEMO_USERNAME = 'demo.admin'
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

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login({ username, password })
      navigate((location.state as { from?: string } | null)?.from ?? '/home', { replace: true })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '로그인에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="ap">
      <div className="ap-card">
        <CubeMark />
        <h1 className="ap-title">PASSBOX</h1>
        <p className="ap-sub">공공기관 계정으로 로그인하세요</p>

        <form className="ap-form" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="login-username">아이디</label>
          <input id="login-username" className="ap-input" placeholder="아이디" value={username}
            onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
          <label className="visually-hidden" htmlFor="login-password">비밀번호</label>
          <input id="login-password" className="ap-input" type="password" placeholder="비밀번호" value={password}
            onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          {error && <p className="ap-error" role="alert">{error}</p>}
          <button type="submit" className="ap-submit" disabled={isSubmitting}>
            {isSubmitting ? '로그인 중…' : '로그인'}
          </button>
        </form>

        {SHOW_DEMO && (
          <button type="button" className="ap-demo"
            onClick={() => { setUsername(DEMO_USERNAME); setPassword(DEMO_PASSWORD); setError('') }}>
            데모 계정 자동 입력 ({DEMO_USERNAME})
          </button>
        )}
      </div>
    </div>
  )
}
