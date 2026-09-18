import { apiClient } from './client'

export async function getDashboardSummary(): Promise<unknown> {
  const { data } = await apiClient.get('/operations/dashboard')
  return data
}
// 대시보드용 데이터를 조회하는 API 진입점입니다.
