// 로그인처럼 사이드바가 필요 없는 화면에서 공통으로 쓰는 단순 레이아웃입니다.
import { Link, Outlet } from 'react-router-dom'
import { ThemeToggle } from '../components/common/ThemeToggle'

export function AuthLayout() {
  return (
    <main className="auth-layout">
      <Link to="/" className="auth-brand">← PASSBOX</Link>
      <ThemeToggle className="auth-theme" />
      <section className="auth-card"><Outlet /></section>
    </main>
  )
}
