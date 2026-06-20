import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/features/auth/services/authApi'
import { useAuth } from './useAuth'

export function useLogout() {
  const navigate = useNavigate()
  const { clearSession } = useAuth()
  const [isLoading, setIsLoading] = useState(false)

  async function logout(): Promise<void> {
    setIsLoading(true)
    try {
      // Best-effort: fire and forget, don't block on network errors
      await authApi.logout()
    } catch {
      // Network error is acceptable — we still clear locally
    } finally {
      clearSession()
      setIsLoading(false)
      navigate('/login', { replace: true })
    }
  }

  return { logout, isLoading }
}
