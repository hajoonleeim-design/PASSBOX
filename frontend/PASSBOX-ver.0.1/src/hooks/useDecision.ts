import { useCallback, useEffect, useState } from 'react'
import { getApiErrorCode } from '../api/client'
import { approveDecisionSource, getDecisionSource, rejectDecisionSource } from '../api/decisionSource'
import type { ClassificationDecision, DecisionActor } from '../types/decision'

export function useDecision(requestId: string | undefined) {
  const [decision, setDecision] = useState<ClassificationDecision | null>(null); const [isLoading, setIsLoading] = useState(true); const [errorCode, setErrorCode] = useState('')
  const refresh = useCallback(async () => { if (!requestId) return; try { setErrorCode(''); setDecision(await getDecisionSource(requestId)) } catch (error) { setErrorCode(getApiErrorCode(error) ?? (error instanceof Error ? error.message : 'NETWORK_ERROR')) } finally { setIsLoading(false) } }, [requestId])
  useEffect(() => { void refresh() }, [refresh])
  const approve = async (actor: DecisionActor) => { if (!requestId) return; const next = await approveDecisionSource(requestId, actor); setDecision(next) }
  const reject = async (reason: string, actor: DecisionActor) => { if (!requestId) return; const next = await rejectDecisionSource(requestId, { reason, actor }); setDecision(next) }
  return { decision, isLoading, errorCode, refresh, approve, reject }
}
// 판정 결과를 조회하고 승인·반려 후 최신 결과로 갱신하는 Hook입니다.
