import { useContext } from 'react'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'

export function useAuth(): AuthContextValue {
  return useContext(AuthContext)
}
