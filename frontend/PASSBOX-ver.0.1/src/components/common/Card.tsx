import type { HTMLAttributes, PropsWithChildren } from 'react'
export function Card({ children, className = '', ...props }: PropsWithChildren<HTMLAttributes<HTMLElement>>) { return <section className={`card ${className}`.trim()} {...props}>{children}</section> }
// 내용을 테두리와 여백이 있는 카드 모양으로 감싸는 공통 컴포넌트입니다.
