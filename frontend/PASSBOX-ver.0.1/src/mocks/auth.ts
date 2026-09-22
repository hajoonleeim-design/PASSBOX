import type { ChangePasswordInput } from '../api/auth'
import type { LoginCredentials, UserRole, UserSession } from '../types/auth'

interface DevelopmentAccount { username: string; password: string; displayName: string; role: UserRole; permissions: string[] }
const accounts: DevelopmentAccount[] = [
  { username: 'test-user', password: 'Test1234!', displayName: '테스트 사용자', role: 'USER', permissions: [] },
  { username: 'test-operator', password: 'Test1234!', displayName: '테스트 운영자', role: 'OPERATOR', permissions: ['dashboard:read'] },
  { username: 'test-approver', password: 'Test1234!', displayName: '테스트 승인자', role: 'APPROVER', permissions: ['approval:write'] },
  { username: 'test-admin', password: 'Test1234!', displayName: '테스트 관리자', role: 'ADMIN', permissions: ['policy:read', 'policy:write', 'dashboard:read', 'audit:read', 'approval:write'] },
]

const DEV_SESSION_KEY = 'passbox_dev_session'
const DEV_LOGOUT_KEY = 'passbox_dev_logged_out'

export async function mockLogin(credentials: LoginCredentials): Promise<UserSession> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 350))
  const account = accounts.find((item) => item.username === credentials.username && item.password === credentials.password)
  if (!account) throw new Error('사용자 ID 또는 비밀번호를 확인해 주세요.')
  const session: UserSession = { userId: `dev-${account.username}`, displayName: account.displayName, institutionId: 'DEV-TEST-ORG', institutionName: '국가보안기술연구소', role: account.role, permissions: account.permissions, expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString() }
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(DEV_SESSION_KEY, JSON.stringify(session))
    window.sessionStorage.removeItem(DEV_LOGOUT_KEY)
  }
  return session
}

export async function mockGetSession(): Promise<UserSession | null> {
  if (typeof window === 'undefined') return null
  if (window.sessionStorage.getItem(DEV_LOGOUT_KEY) === 'true') return null
  const saved = window.sessionStorage.getItem(DEV_SESSION_KEY)
  if (saved) {
    try {
      return JSON.parse(saved) as UserSession
    } catch {
      // ignore
    }
  }
  // 기본 데모 세션 제공 (개발 및 프리뷰 원활화)
  const defaultSession: UserSession = {
    userId: 'dev-test-admin',
    displayName: '보안 관리자',
    institutionId: 'DEV-TEST-ORG',
    institutionName: '국가보안기술연구소',
    role: 'ADMIN',
    permissions: ['policy:read', 'policy:write', 'dashboard:read', 'audit:read', 'approval:write'],
    expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  }
  window.sessionStorage.setItem(DEV_SESSION_KEY, JSON.stringify(defaultSession))
  return defaultSession
}

export async function mockChangePassword(input: ChangePasswordInput): Promise<void> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 200))
  if (!input.currentPassword.trim()) throw new Error('INVALID_CURRENT_PASSWORD')
  if (input.currentPassword === input.newPassword) throw new Error('PASSWORD_REUSE')
}
// 백엔드 없이 로그인 화면을 개발·확인할 수 있도록 만든 가짜 인증 데이터/함수입니다.
