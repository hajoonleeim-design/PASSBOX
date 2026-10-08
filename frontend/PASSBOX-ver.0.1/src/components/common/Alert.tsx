import type { PropsWithChildren, ReactNode } from 'react'
type AlertVariant = 'info' | 'success' | 'warning' | 'danger'
const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const
const icons: Record<AlertVariant, ReactNode> = {
  info: <svg viewBox="0 0 12 12" width="12" height="12" {...stroke}><path d="M6 5.5v3.5" /><circle cx="6" cy="3.2" r=".4" /></svg>,
  success: <svg viewBox="0 0 12 12" width="12" height="12" {...stroke}><path d="M2.5 6.4l2.3 2.3 4.7-5" /></svg>,
  warning: <svg viewBox="0 0 12 12" width="12" height="12" {...stroke}><path d="M6 2.8v3.8" /><circle cx="6" cy="9" r=".4" /></svg>,
  danger: <svg viewBox="0 0 12 12" width="12" height="12" {...stroke}><path d="M3 3l6 6M9 3l-6 6" /></svg>,
}
export function Alert({ children, variant = 'info', title }: PropsWithChildren<{ variant?: AlertVariant; title?: string }>) { return <div className={`alert alert--${variant}`} role={variant === 'danger' ? 'alert' : 'status'}><span className="alert__icon" aria-hidden="true">{icons[variant]}</span><div>{title && <strong>{title}</strong>}<div>{children}</div></div></div> }
// 성공·안내·경고·오류 메시지를 공통 스타일로 보여 주는 컴포넌트입니다.
