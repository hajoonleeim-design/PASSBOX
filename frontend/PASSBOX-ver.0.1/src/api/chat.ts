import { apiClient } from './client'

export async function submitChatRequest(): Promise<unknown> {
  const { data } = await apiClient.post('/chat/requests')
  return data
}
// 일반 채팅 기능에서 사용할 API 진입점입니다.
