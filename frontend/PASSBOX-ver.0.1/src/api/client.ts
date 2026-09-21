import axios, { AxiosError } from 'axios'

export interface ApiError {
  status?: number
  message: string
  code?: string
  requestId?: string
}

const LAST_REQUEST_ID_KEY = 'passbox_last_request_id'

export function getLastRequestId(): string | undefined {
  if (typeof window === 'undefined') return undefined
  return window.sessionStorage.getItem(LAST_REQUEST_ID_KEY) ?? undefined
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const ACCESS_TOKEN_KEY = 'passbox_access_token'

export function getAccessToken(): string | null {
  return typeof window === 'undefined' ? null : window.sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token: string | null): void {
  if (typeof window === 'undefined') return
  if (token) window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  else window.sessionStorage.removeItem(ACCESS_TOKEN_KEY)
}

// axios 인스턴스: 모든 실제 백엔드 요청이 공통 주소, 시간 제한, 헤더를 사용하게 합니다.
export const apiClient = axios.create({
  baseURL: apiBaseUrl || undefined,
  timeout: 15_000,
  headers: { Accept: 'application/json' },
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 응답 오류를 화면에서 다루기 쉬운 ApiError 형태로 통일합니다.
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string; detail?: string; code?: string }>) => {
    const apiError: ApiError = {
      status: error.response?.status,
      code: error.response?.data?.code,
      requestId: error.response?.headers?.['x-request-id'],
      message: error.response?.data?.message ?? error.response?.data?.detail ?? (error.request ? '네트워크 연결을 확인한 뒤 다시 시도해 주세요.' : '요청을 처리하지 못했습니다.'),
    }
    if (apiError.requestId && typeof window !== 'undefined') {
      window.sessionStorage.setItem(LAST_REQUEST_ID_KEY, apiError.requestId)
    }
    return Promise.reject(apiError)
  },
)
