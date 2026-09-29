import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ReactNode } from 'react'
import { usePermission } from './usePermission'
import { AuthContext, type AuthContextValue } from '../stores/authContextValue'
import type { UserRole, UserSession } from '../types/auth'

function makeSession(role: UserRole, permissions: string[] = []): UserSession {
  return {
    userId: 'u1',
    displayName: '테스트 사용자',
    institutionId: 't1',
    institutionName: '테스트 기관',
    role,
    permissions,
    expiresAt: new Date(Date.now() + 60_000).toISOString(),
  }
}

function withSession(session: UserSession | null) {
  const value: AuthContextValue = {
    session,
    isAuthenticated: session !== null,
    isInitializing: false,
    login: async () => {},
    logout: async () => {},
  }
  return ({ children }: { children: ReactNode }) => (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  )
}

describe('usePermission', () => {
  it('로그인하지 않은 사용자는 항상 권한이 없다', () => {
    const { result } = renderHook(() => usePermission(['USER']), { wrapper: withSession(null) })
    expect(result.current).toBe(false)
  })

  it('역할 제한이 없으면 로그인한 사용자는 통과한다', () => {
    const { result } = renderHook(() => usePermission(), { wrapper: withSession(makeSession('USER')) })
    expect(result.current).toBe(true)
  })

  it('허용 목록에 있는 역할은 통과한다', () => {
    const { result } = renderHook(() => usePermission(['APPROVER']), {
      wrapper: withSession(makeSession('APPROVER')),
    })
    expect(result.current).toBe(true)
  })

  it('허용 목록에 없는 역할은 막는다', () => {
    const { result } = renderHook(() => usePermission(['APPROVER']), {
      wrapper: withSession(makeSession('OPERATOR')),
    })
    expect(result.current).toBe(false)
  })

  it('SECURITY_ADMIN은 APPROVER 전용 화면도 볼 수 있다', () => {
    const { result } = renderHook(() => usePermission(['APPROVER']), {
      wrapper: withSession(makeSession('SECURITY_ADMIN')),
    })
    expect(result.current).toBe(true)
  })

  it('SECURITY_ADMIN도 APPROVER가 허용 목록에 없으면 통과하지 못한다', () => {
    const { result } = renderHook(() => usePermission(['USER']), {
      wrapper: withSession(makeSession('SECURITY_ADMIN')),
    })
    expect(result.current).toBe(false)
  })

  it('permission 문자열이 세션에 없으면 막는다', () => {
    const { result } = renderHook(() => usePermission(undefined, 'policy:write'), {
      wrapper: withSession(makeSession('ADMIN', ['policy:read'])),
    })
    expect(result.current).toBe(false)
  })

  it('permission 문자열이 세션에 있으면 통과한다', () => {
    const { result } = renderHook(() => usePermission(undefined, 'policy:write'), {
      wrapper: withSession(makeSession('ADMIN', ['policy:write'])),
    })
    expect(result.current).toBe(true)
  })
})
