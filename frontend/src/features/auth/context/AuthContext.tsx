import { createContext } from 'react'
import type { AuthContextValue } from '@/shared/types/auth'

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  isAuthenticated: false,
  hasPermission: () => false,
  setSession: () => undefined,
  clearSession: () => undefined,
})
