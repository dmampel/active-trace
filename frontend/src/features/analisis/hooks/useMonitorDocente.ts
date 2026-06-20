import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { getMonitorDocente, type MonitorFiltros } from '../services/analisisApi'

export function useMonitorDocente(comisionId: string) {
  // Identity from session, never from URL params
  const { user } = useAuth()

  const [filtros, setFiltros] = useState<MonitorFiltros>({})

  const query = useQuery({
    queryKey: ['monitor', comisionId, user?.id, filtros],
    queryFn: () => getMonitorDocente(comisionId, filtros),
    enabled: !!comisionId && !!user,
  })

  const clearFiltros = () => setFiltros({})

  return {
    alumnos: query.data ?? [],
    isLoading: query.isLoading,
    filtros,
    setFiltros,
    clearFiltros,
  }
}
