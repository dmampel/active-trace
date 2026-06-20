import { useMutation } from '@tanstack/react-query'
import { enviarComunicacion } from '../services/comunicacionApi'
import type { EnviarComunicacionPayload } from '../types'

export function useEnviarComunicacion() {
  const mutation = useMutation({
    mutationFn: (payload: EnviarComunicacionPayload) => enviarComunicacion(payload),
  })

  return {
    enviar: (payload: EnviarComunicacionPayload) => mutation.mutateAsync(payload),
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error as (Error & { response?: { data?: { detail?: string } } }) | null,
    reset: mutation.reset,
  }
}
