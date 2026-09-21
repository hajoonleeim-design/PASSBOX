import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { getSession, login as loginRequest, logout as logoutRequest } from '../api/auth'
import type { LoginCredentials, UserSession } from '../types/auth'
import { AuthContext } from './authContextValue'

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<UserSession | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    let active = true
    void getSession().then((nextSession) => {
      if (active) setSession(nextSession)
    }).catch(() => {
      if (active) setSession(null)
    }).finally(() => {
      if (active) setIsInitializing(false)
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!session) return
    const remainingMs = new Date(session.expiresAt).getTime() - Date.now()
    const timeoutId = window.setTimeout(() => setSession(null), Math.max(0, remainingMs))
    return () => window.clearTimeout(timeoutId)
  }, [session])

  const login = useCallback(async (credentials: LoginCredentials) => {
    const nextSession = await loginRequest(credentials)
    setSession(nextSession)
  }, [])

  const logout = useCallback(async () => {
    await logoutRequest()
    setSession(null)
  }, [])

  const value = useMemo(() => ({
    session,
    isAuthenticated: session !== null,
    isInitializing,
    login,
    logout,
  }), [isInitializing, login, logout, session])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
