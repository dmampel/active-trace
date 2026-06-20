import { useState } from 'react'
import { authApi } from '@/features/auth/services/authApi'

export function useForgotPassword() {
  const [isLoading, setIsLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function forgotPassword(email: string): Promise<void> {
    setIsLoading(true)
    setError(null)

    try {
      await authApi.forgotPassword({ email })
      setSent(true)
    } catch {
      // Still show success to avoid email enumeration
      setSent(true)
    } finally {
      setIsLoading(false)
    }
  }

  return { forgotPassword, isLoading, sent, error }
}
