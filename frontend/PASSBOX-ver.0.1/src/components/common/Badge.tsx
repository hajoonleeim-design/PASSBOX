import type { PropsWithChildren } from 'react'

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'
export function Badge({ children, variant = 'neutral' }: PropsWithChildren<{ variant?: BadgeVariant }>) {
  return <span className={`badge badge--${variant}`}>{children}</span>
}
// 짧은 상태 값을 색 있는 작은 라벨로 표시하는 기본 컴포넌트입니다.
