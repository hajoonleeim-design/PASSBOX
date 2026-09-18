export function LoadingState({ label = '불러오는 중입니다.' }: { label?: string }) { return <p role="status">{label}</p> }
export function EmptyState({ label }: { label: string }) { return <p>{label}</p> }
export function ErrorState({ label }: { label: string }) { return <p role="alert">{label}</p> }
// 데이터가 없거나, 불러오는 중이거나, 오류일 때 보여 줄 공통 화면 조각입니다.
