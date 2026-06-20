import { useState, useCallback, type ReactNode } from 'react'
import { AuthContext } from './AuthContext'
import { tokenStorage } from '@/shared/services/tokenStorage'
import type { Session, User, PermissionString } from '@/shared/types/auth'

const USER_KEY = 'auth_user'

function loadSessionFromStorage(): { session: Session | null; user: User | null } {
  const accessToken = tokenStorage.getAccessToken()
  const refreshToken = tokenStorage.getRefreshToken()
  const userRaw = localStorage.getItem(USER_KEY)

  if (!accessToken || !refreshToken || !userRaw) {
    return { session: null, user: null }
  }

  try {
    const user = JSON.parse(userRaw) as User
    return {
      session: { access_token: accessToken, refresh_token: refreshToken, user },
      user,
    }
  } catch {
    return { session: null, user: null }
  }
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const initialState = loadSessionFromStorage()
  const [session, setSessionState] = useState<Session | null>(initialState.session)
  const [user, setUser] = useState<User | null>(initialState.user)

  const setSession = useCallback((newSession: Session) => {
    tokenStorage.setAccessToken(newSession.access_token)
    tokenStorage.setRefreshToken(newSession.refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(newSession.user))
    setSessionState(newSession)
    setUser(newSession.user)
  }, [])

  const clearSession = useCallback(() => {
    tokenStorage.clear()
    localStorage.removeItem(USER_KEY)
    setSessionState(null)
    setUser(null)
  }, [])

  const hasPermission = useCallback(
    (perm: PermissionString): boolean => {
      if (!user) return false
      return user.permissions.includes(perm)
    },
    [user],
  )

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isAuthenticated: session !== null,
        hasPermission,
        setSession,
        clearSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
