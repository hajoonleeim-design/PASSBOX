import { useCallback, useEffect, useState } from 'react'
import { getAudit } from '../api/audit'
import type { AuditActor, AuditRecord } from '../types/audit'

export function useAudit(requestId: string | undefined, actor: AuditActor | null) {
  const [audit, setAudit] = useState<AuditRecord | null>(null); const [isLoading, setIsLoading] = useState(Boolean(requestId)); const [errorCode, setErrorCode] = useState('')
  const refresh = useCallback(async () => { if (!requestId || !actor) return; try { setErrorCode(''); setAudit(await getAudit(requestId, actor)) } catch (error) { setErrorCode(error instanceof Error ? error.message : 'NETWORK_ERROR') } finally { setIsLoading(false) } }, [actor, requestId])
  useEffect(() => { void refresh() }, [refresh])
  return { audit, isLoading, errorCode, refresh }
}
// 감사 기록을 불러오는 중/성공/실패 상태를 화면에 전달하는 Hook입니다.
