import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob } from '../api/jobs'
import type { AnalysisJob } from '../types/security'

const terminalStatuses = new Set(['COMPLETED', 'BLOCKED', 'FAILED', 'CANCELLED'])
// 끝난 작업은 더 이상 서버에 반복 조회하지 않습니다.
export const isTerminalJob = (job?: AnalysisJob | null) => Boolean(job && terminalStatuses.has(job.status))

// 분석 작업의 상태를 일정 간격으로 다시 가져오는 Hook입니다.
// 작업이 끝나거나 오류/미존재 상태가 되면 polling을 중지합니다.
export function useJobPolling(jobId: string | undefined, pollIntervalMs = 2_500) {
  const [job, setJob] = useState<AnalysisJob | null>(null); const [isLoading, setIsLoading] = useState(true); const [networkError, setNetworkError] = useState(''); const [notFound, setNotFound] = useState(false); const timerRef = useRef<number | null>(null)
  const refresh = useCallback(async () => { if (!jobId) return; try { setNetworkError(''); const next = await getJob(jobId); setJob(next); setNotFound(false) } catch (error) { if (error instanceof Error && error.message === 'NOT_FOUND') setNotFound(true); else setNetworkError('분석 상태를 확인할 수 없습니다. 네트워크 연결을 확인한 뒤 다시 조회해 주세요.') } finally { setIsLoading(false) } }, [jobId])
  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => { if (!jobId || isTerminalJob(job) || networkError || notFound) return; timerRef.current = window.setInterval(() => void refresh(), pollIntervalMs); return () => { if (timerRef.current !== null) window.clearInterval(timerRef.current) } }, [job, jobId, networkError, notFound, pollIntervalMs, refresh])
  return { job, isLoading, networkError, notFound, refresh, setJob }
}
