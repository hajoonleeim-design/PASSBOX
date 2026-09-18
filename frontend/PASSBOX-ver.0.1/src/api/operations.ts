import type { UserRole } from '../types/auth'
import type { OperationsDashboard } from '../types/operations'
import { apiClient } from './client'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

export async function getOperationsDashboard(scenario: string, role: UserRole): Promise<OperationsDashboard> {
  if (useMock) {
    const { mockGetOperationsDashboard } = await import('../mocks/operations')
    return mockGetOperationsDashboard(scenario, role)
  }
  if (!['ADMIN', 'OPERATOR'].includes(role)) throw new Error('FORBIDDEN')
  const { data } = await apiClient.get<OperationsDashboard>('/operations/dashboard')
  return data
}
// 운영 현황 대시보드 데이터를 제공하는 API 계층입니다.
