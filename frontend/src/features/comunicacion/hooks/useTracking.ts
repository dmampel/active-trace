import { useQuery } from '@tanstack/react-query'
import { getTracking } from '../services/comunicacionApi'
import { ESTADOS_FINALES, type MensajeEstado } from '../types'

export function useTracking(comisionId: string) {
  const query = useQuery({
    queryKey: ['tracking', comisionId],
    queryFn: () => getTracking(comisionId),
    enabled: !!comisionId,
    refetchInterval: (data) => {
      const mensajes = data.state.data
      if (!mensajes || mensajes.length === 0) return false
      const hayEnTransito = mensajes.some(
        (m) => !ESTADOS_FINALES.includes(m.estado as MensajeEstado),
      )
      return hayEnTransito ? 3000 : false
    },
    refetchIntervalInBackground: false,
  })

  return {
    mensajes: query.data ?? [],
    isLoading: query.isLoading,
  }
}
