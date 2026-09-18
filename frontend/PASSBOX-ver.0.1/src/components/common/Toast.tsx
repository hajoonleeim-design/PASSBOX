export function Toast({ message }: { message: string }) { return <div role="status" className="toast">{message}</div> }
// 작업 완료나 오류를 잠시 알려 주는 작은 알림 컴포넌트입니다.
