import { useCallback, useEffect, useState } from 'react'
import { getApiErrorCode } from '../api/client'
import { getOperationsDashboard } from '../api/operations'
import type { UserRole } from '../types/auth'
import type { OperationsDashboard } from '../types/operations'

// 운영 대시보드 데이터를 가져오는 Hook입니다. 역할(role)에 따라 서버가 다른 데이터를 줄 수 있습니다.
export function useOperations(scenario: string, role: UserRole | undefined) {
  const [dashboard, setDashboard] = useState<OperationsDashboard | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorCode, setErrorCode] = useState('')

  const refresh = useCallback(async () => {
    if (!role) return
    setIsLoading(true)
    setErrorCode('')
    try {
      setDashboard(await getOperationsDashboard(scenario, role))
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? (error instanceof Error ? error.message : 'NETWORK_ERROR'))
    } finally {
      setIsLoading(false)
    }
  }, [role, scenario])

  useEffect(() => { void refresh() }, [refresh])
  return { dashboard, isLoading, errorCode, refresh }
}
