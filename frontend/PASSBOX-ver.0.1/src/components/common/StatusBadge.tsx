import { Badge } from './Badge'

export type StatusLabel = '대기' | '업로드 중' | '업로드 완료' | '검증 중' | '검증 완료' | '접수' | '검사' | '파싱' | '탐지' | '마스킹' | '승인대기' | '전송' | '답변검사' | '완료' | '차단' | '실패' | '취소'
const variants: Record<StatusLabel, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = { 대기: 'neutral', '업로드 중': 'info', '업로드 완료': 'info', '검증 중': 'warning', '검증 완료': 'success', 접수: 'info', 검사: 'info', 파싱: 'info', 탐지: 'warning', 마스킹: 'info', 승인대기: 'warning', 전송: 'info', 답변검사: 'info', 완료: 'success', 차단: 'danger', 실패: 'danger', 취소: 'neutral' }
export function StatusBadge({ label }: { label: StatusLabel }) {
  return <Badge variant={variants[label]}><span aria-hidden="true">●</span> {label}</Badge>
}
// 상태 문자열을 Badge 컴포넌트의 색상 종류로 변환해 표시합니다.
