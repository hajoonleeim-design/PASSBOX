import { useCallback, useEffect, useRef, useState } from 'react'
import { getApiErrorCode } from '../api/client'
import { getChatRequest, retryChatRequest } from '../api/aiChat'
import type { AIChatResponse } from '../types/aiChat'

const terminal = new Set(['VERIFIED', 'BLOCKED', 'FAILED'])
export function useChatRequest(requestId: string | undefined, pollIntervalMs = 2_500) {
  const [chat, setChat] = useState<AIChatResponse | null>(null); const [isLoading, setIsLoading] = useState(Boolean(requestId)); const [errorCode, setErrorCode] = useState(''); const timerRef = useRef<number | null>(null)
  const refresh = useCallback(async () => { if (!requestId) return; try { setErrorCode(''); setChat(await getChatRequest(requestId)) } catch (error) { setErrorCode(getApiErrorCode(error) ?? (error instanceof Error ? error.message : 'NETWORK_ERROR')) } finally { setIsLoading(false) } }, [requestId])
  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => { if (!requestId || !chat || terminal.has(chat.responseStatus) || errorCode) return; timerRef.current = window.setInterval(() => void refresh(), pollIntervalMs); return () => { if (timerRef.current !== null) window.clearInterval(timerRef.current) } }, [chat, errorCode, pollIntervalMs, refresh, requestId])
  const retry = async () => { if (!requestId) return; const next = await retryChatRequest(requestId); setChat(next); setErrorCode('') }
  return { chat, setChat, isLoading, errorCode, refresh, retry }
}
// AI 채팅 요청 한 건의 조회와 재시도 상태를 관리하는 Hook입니다.
