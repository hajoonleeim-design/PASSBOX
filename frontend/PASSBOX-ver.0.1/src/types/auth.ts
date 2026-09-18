export type UserRole = 'USER' | 'OPERATOR' | 'APPROVER' | 'SECURITY_ADMIN' | 'ADMIN'

export interface UserSession {
  userId: string
  displayName: string
  institutionId: string
  institutionName: string
  role: UserRole
  permissions: string[]
  expiresAt: string
}

export interface LoginCredentials {
  username: string
  password: string
  tenantId?: number
}

export type SessionStatus = 'ACTIVE' | 'EXPIRING' | 'EXPIRED'
// 로그인 요청과 로그인 후 유지할 사용자 세션의 데이터 모양을 정의합니다.
