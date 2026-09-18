import { useCallback, useEffect, useState } from 'react'
import { getPolicy, getPolicyHistory, updatePolicy } from '../api/policy'
import type { PolicyActor, PolicyChangeHistory, SecurityPolicy } from '../types/policy'

function policyErrorCode(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null) {
    const status = (error as { status?: number }).status
    if (status === 403) return 'FORBIDDEN'
    if (status === 404) return 'NOT_FOUND'
    const message = (error as { message?: string }).message
    if (message) return message
  }
  return 'NETWORK_ERROR'
}

export function usePolicy(policyId: string, actor: PolicyActor | null) {
  const [policy, setPolicy] = useState<SecurityPolicy | null>(null)
  const [history, setHistory] = useState<PolicyChangeHistory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorCode, setErrorCode] = useState('')
  const refresh = useCallback(async () => {
    if (!actor) return
    try {
      setErrorCode('')
      const [next, nextHistory] = await Promise.all([getPolicy(policyId, actor), getPolicyHistory(policyId, actor)])
      setPolicy(next)
      setHistory(nextHistory)
    } catch (error) {
      setErrorCode(policyErrorCode(error))
    } finally {
      setIsLoading(false)
    }
  }, [actor, policyId])
  useEffect(() => { void refresh() }, [refresh])
  const save = async (draft: SecurityPolicy, reason: string) => {
    if (!actor) return
    const next = await updatePolicy(policyId, { policy: draft, changeReason: reason, actor })
    setPolicy(next)
    setHistory(await getPolicyHistory(policyId, actor))
  }
  return { policy, history, isLoading, errorCode, refresh, save }
}
// 정책 데이터를 불러오는 중/성공/실패 상태를 관리하는 Hook입니다.
