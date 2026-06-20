import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/features/auth/services/authApi'
import { useAuth } from './useAuth'

export function useVerify2fa() {
  const navigate = useNavigate()
  const { setSession } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function verify(tempToken: string, code: string): Promise<void> {
    setIsLoading(true)
    setError(null)

    try {
      const session = await authApi.verify2fa({ temp_token: tempToken, code })
      setSession(session)
      navigate('/', { replace: true })
    } catch {
      setError('Código incorrecto. Intentá nuevamente.')
    } finally {
      setIsLoading(false)
    }
  }

  return { verify, isLoading, error }
}
