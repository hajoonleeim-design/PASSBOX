type IconProps = { className?: string }

// 랜딩페이지 전용 심플 라인 아이콘입니다. 외부 아이콘 라이브러리 없이
// 24x24 stroke 기준으로 통일해 쇼룸 섹션의 타이포그래피와 나란히 둡니다.

export function NetworkLockIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="5" r="2.2" />
      <circle cx="5" cy="14" r="2.2" />
      <circle cx="19" cy="14" r="2.2" />
      <path d="M12 7.2V11M10.3 12.8 6.8 12.3M13.7 12.8l3.5-.5" />
      <rect x="8.6" y="15.5" width="6.8" height="6" rx="1.4" />
      <path d="M10.2 15.5v-1.4a1.8 1.8 0 0 1 3.6 0v1.4" />
    </svg>
  )
}

export function AlertDocIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3.5h7l3.5 3.5V20a.6.6 0 0 1-.6.6H7a.6.6 0 0 1-.6-.6V4.1a.6.6 0 0 1 .6-.6Z" />
      <path d="M14 3.5V7h3.5" />
      <path d="M12 10.5v4" />
      <circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function HourglassIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3.5h10M7 20.5h10" />
      <path d="M7.5 3.5v3.2c0 1.6 1.2 2.9 3 3.8-1.8.9-3 2.2-3 3.8v2.7M16.5 3.5v3.2c0 1.6-1.2 2.9-3 3.8 1.8.9 3 2.2 3 3.8v2.7" />
    </svg>
  )
}

export function GradeIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3 4.5 6.3v5.4c0 4.4 3.1 7.6 7.5 9 4.4-1.4 7.5-4.6 7.5-9V6.3Z" />
      <path d="M8.7 12.2 11 14.5l4.3-5" />
    </svg>
  )
}

export function VaultIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="4.5" width="16" height="15" rx="2" />
      <circle cx="12" cy="12" r="3.4" />
      <path d="M12 8.6v.9M12 13.5v.9M15.4 12h-.9M9.5 12h-.9" />
    </svg>
  )
}

export function MaskIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3.5h7l3.5 3.5V20a.6.6 0 0 1-.6.6H7a.6.6 0 0 1-.6-.6V4.1a.6.6 0 0 1 .6-.6Z" />
      <path d="M14 3.5V7h3.5" />
      <rect x="8" y="11.2" width="8" height="2.1" rx="1.05" fill="currentColor" stroke="none" />
      <rect x="8" y="15.1" width="5" height="2.1" rx="1.05" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function ChainIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3.2" y="8.5" width="7" height="7" rx="2.2" />
      <rect x="13.8" y="8.5" width="7" height="7" rx="2.2" />
      <path d="M10.2 12h3.6" />
    </svg>
  )
}
