import type { PropsWithChildren } from 'react'
type AlertVariant = 'info' | 'success' | 'warning' | 'danger'
const icons: Record<AlertVariant, string> = { info: 'i', success: '✓', warning: '!', danger: '×' }
export function Alert({ children, variant = 'info', title }: PropsWithChildren<{ variant?: AlertVariant; title?: string }>) { return <div className={`alert alert--${variant}`} role={variant === 'danger' ? 'alert' : 'status'}><span className="alert__icon" aria-hidden="true">{icons[variant]}</span><div>{title && <strong>{title}</strong>}<div>{children}</div></div></div> }
// 성공·안내·경고·오류 메시지를 공통 스타일로 보여 주는 컴포넌트입니다.
