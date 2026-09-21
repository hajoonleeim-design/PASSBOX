import { apiClient, getAccessToken, setAccessToken } from './client'
import type { LoginCredentials, UserRole, UserSession } from '../types/auth'

const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL

interface BackendLoginResponse {
  access_token: string
  token_type: string
  user_id: number
  tenant_id: number
  username: string
  display_name: string
  role: string
  tenant_name: string
}

interface BackendMeResponse {
  user_id: number
  tenant_id: number
  username: string
  display_name: string
  role: string
  tenant_name: string
}

export interface ChangePasswordInput {
  currentPassword: string
  newPassword: string
}

interface BackendPasswordChangeResponse {
  status: string
}

export async function login(credentials: LoginCredentials): Promise<UserSession> {
  if (useMock) {
    const { mockLogin } = await import('../mocks/auth')
    return mockLogin(credentials)
  }

  const { data } = await apiClient.post<BackendLoginResponse>('/auth/login', {
    tenant_id: credentials.tenantId ?? 1,
    username: credentials.username,
    password: credentials.password,
  })
  setAccessToken(data.access_token)
  return toUserSession(data, data.access_token)
}

export async function getSession(): Promise<UserSession | null> {
  if (useMock) {
    const { mockGetSession } = await import('../mocks/auth')
    return mockGetSession()
  }

  const accessToken = getAccessToken()
  if (!accessToken) return null

  try {
    const { data } = await apiClient.get<BackendMeResponse>('/auth/me')
    return toUserSession({
      access_token: accessToken,
      token_type: 'bearer',
      user_id: data.user_id,
      tenant_id: data.tenant_id,
      username: data.username,
      display_name: data.display_name,
      role: data.role,
      tenant_name: data.tenant_name,
    }, accessToken)
  } catch {
    setAccessToken(null)
    return null
  }
}

export async function logout(): Promise<void> {
  setAccessToken(null)
}

export async function changePassword(input: ChangePasswordInput): Promise<void> {
  if (useMock) {
    const { mockChangePassword } = await import('../mocks/auth')
    await mockChangePassword(input)
    return
  }

  await apiClient.post<BackendPasswordChangeResponse>('/auth/password', {
    current_password: input.currentPassword,
    new_password: input.newPassword,
  })
}

function toUserSession(data: BackendLoginResponse, accessToken: string): UserSession {
  const knownRoles: UserRole[] = ['USER', 'OPERATOR', 'APPROVER', 'SECURITY_ADMIN', 'ADMIN']
  const role = knownRoles.includes(data.role as UserRole) ? data.role as UserRole : 'USER'
  return {
    userId: String(data.user_id),
    displayName: data.display_name,
    institutionId: String(data.tenant_id),
    institutionName: data.tenant_name,
    role,
    permissions: [],
    expiresAt: tokenExpiresAt(accessToken),
  }
}

function tokenExpiresAt(token: string): string {
  try {
    const encodedPayload = token.split('.')[1]
    const normalizedPayload = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
    const paddedPayload = normalizedPayload.padEnd(Math.ceil(normalizedPayload.length / 4) * 4, '=')
    const payload = JSON.parse(window.atob(paddedPayload)) as { exp?: number }
    if (typeof payload.exp === 'number') return new Date(payload.exp * 1000).toISOString()
  } catch {
    // 서버가 토큰 유효성을 최종 판단하므로 여기서는 기본 만료 시간을 사용합니다.
  }
  return new Date(Date.now() + 60 * 60 * 1000).toISOString()
}
