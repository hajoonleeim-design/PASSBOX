export function LoadingState({ label = '불러오는 중입니다.' }: { label?: string }) { return <p role="status">{label}</p> }
export function EmptyState({ label }: { label: string }) { return <p>{label}</p> }
export function ErrorState({ label, requestId }: { label: string; requestId?: string }) { const visibleRequestId = requestId ?? getLastRequestId(); return <div role="alert"><p>{label}</p>{visibleRequestId && <small>문의용 Request ID: <code>{visibleRequestId}</code></small>}</div> }
// 데이터가 없거나, 불러오는 중이거나, 오류일 때 보여 줄 공통 화면 조각입니다.
import { getLastRequestId } from '../../api/client'
