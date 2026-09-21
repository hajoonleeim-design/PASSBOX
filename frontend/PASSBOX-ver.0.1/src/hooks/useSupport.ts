import { useCallback, useEffect, useState } from 'react'
import { getApiErrorCode } from '../api/client'
import { createInquiry, getSupportContent } from '../api/support'
import type { CreateInquiryInput, SupportContent, SupportResponse } from '../types/support'

// 지원 페이지의 안내문을 불러오고, 문의 제출 중 상태를 함께 관리합니다.
export function useSupport(scenario: string) {
  const [content, setContent] = useState<SupportContent | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorCode, setErrorCode] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // scenario가 바뀌면 같은 함수도 새 조건으로 만들어져 useEffect가 다시 불러옵니다.
  const refresh = useCallback(async () => {
    setIsLoading(true); setErrorCode('')
    try { setContent(await getSupportContent(scenario)) }
    catch (error) { setErrorCode(getApiErrorCode(error) ?? (error instanceof Error ? error.message : 'NETWORK_ERROR')) }
    finally { setIsLoading(false) }
  }, [scenario])

  useEffect(() => { void refresh() }, [refresh])
  const submit = async (input: CreateInquiryInput): Promise<SupportResponse> => {
    setIsSubmitting(true)
    try { return await createInquiry(input, scenario) }
    finally { setIsSubmitting(false) }
  }
  return { content, isLoading, errorCode, isSubmitting, refresh, submit }
}
