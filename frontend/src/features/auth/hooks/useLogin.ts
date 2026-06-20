import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authApi, type LoginPayload } from '@/features/auth/services/authApi'
import { useAuth } from './useAuth'

interface LocationState {
  from?: { pathname: string }
}

export function useLogin() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setSession } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function login(payload: LoginPayload): Promise<void> {
    setIsLoading(true)
    setError(null)

    try {
      const result = await authApi.login(payload)

      if (result.status === '2fa_required') {
        navigate('/login/2fa', { state: { temp_token: result.temp_token } })
        return
      }

      setSession(result.session)
      const state = location.state as LocationState | null
      const from = state?.from?.pathname ?? '/'
      navigate(from, { replace: true })
    } catch {
      setError('Credenciales inválidas. Verificá tu email y contraseña.')
    } finally {
      setIsLoading(false)
    }
  }

  return { login, isLoading, error }
}
