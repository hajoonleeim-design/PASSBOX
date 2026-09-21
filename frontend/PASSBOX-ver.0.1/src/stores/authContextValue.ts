import { createContext } from 'react'
import type { LoginCredentials, UserSession } from '../types/auth'

export interface AuthContextValue {
  session: UserSession | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
