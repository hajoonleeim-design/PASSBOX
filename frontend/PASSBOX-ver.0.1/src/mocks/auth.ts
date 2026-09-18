import type { LoginCredentials, UserRole, UserSession } from '../types/auth'

interface DevelopmentAccount { username: string; password: string; displayName: string; role: UserRole; permissions: string[] }
const accounts: DevelopmentAccount[] = [
  { username: 'test-user', password: 'Test1234!', displayName: '테스트 사용자', role: 'USER', permissions: [] },
  { username: 'test-operator', password: 'Test1234!', displayName: '테스트 운영자', role: 'OPERATOR', permissions: ['dashboard:read'] },
  { username: 'test-approver', password: 'Test1234!', displayName: '테스트 승인자', role: 'APPROVER', permissions: ['approval:write'] },
  { username: 'test-admin', password: 'Test1234!', displayName: '테스트 관리자', role: 'ADMIN', permissions: ['policy:read', 'policy:write', 'dashboard:read', 'audit:read', 'approval:write'] },
]

export async function mockLogin(credentials: LoginCredentials): Promise<UserSession> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 350))
  const account = accounts.find((item) => item.username === credentials.username && item.password === credentials.password)
  if (!account) throw new Error('사용자 ID 또는 비밀번호를 확인해 주세요.')
  return { userId: `dev-${account.username}`, displayName: account.displayName, institutionId: 'DEV-TEST-ORG', institutionName: '테스트 기관', role: account.role, permissions: account.permissions, expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString() }
}

export async function mockGetSession(): Promise<UserSession | null> {
  return null
}
// 백엔드 없이 로그인 화면을 개발·확인할 수 있도록 만든 가짜 인증 데이터/함수입니다.
