import type { SecurityGrade } from '../../types/security'

const labels: Record<SecurityGrade, string> = { C: 'C등급 · 전송 차단', S: 'S등급 · 승인 필요', O: 'O등급 · 검증 완료' }
const icons: Record<SecurityGrade, string> = { C: '⛔', S: '⚠', O: '✓' }
export function GradeBadge({ grade }: { grade: SecurityGrade }) { return <span className={`grade grade--${grade}`}><span aria-hidden="true">{icons[grade]}</span> {labels[grade]}</span> }
