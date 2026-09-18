import type { UserRole } from '../types/auth'
import type { OperationsDashboard } from '../types/operations'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

export async function getOperationsDashboard(scenario: string, role: UserRole): Promise<OperationsDashboard> {
  if (useMock) {
    const { mockGetOperationsDashboard } = await import('../mocks/operations')
    return mockGetOperationsDashboard(scenario, role)
  }
  throw new Error('OPERATIONS_API_UNAVAILABLE')
}
// 운영 현황 대시보드 데이터를 제공하는 API 계층입니다.
