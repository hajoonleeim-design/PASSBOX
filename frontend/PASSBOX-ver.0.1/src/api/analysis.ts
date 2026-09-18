import { apiClient } from './client'

export async function getAnalysisResult(requestId: string): Promise<unknown> {
  const { data } = await apiClient.get(`/analysis/${requestId}`)
  return data
}
// 분석 결과 조회 API를 담당합니다. 화면은 이 파일을 통해서만 데이터를 받도록 분리합니다.
