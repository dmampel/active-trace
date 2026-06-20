import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getEquiposDocente,
  getAsignacionesTenant,
  crearAsignacionesMasivas,
  clonarEquipo,
  modificarVigenciaEquipo,
} from '../services/equiposApi'
import type {
  FiltrosAsignaciones,
  AsignacionMasivaPayload,
  ClonarEquipoPayload,
  ModificarVigenciaPayload,
} from '../types'

// Hook for docente's own equipos — identity comes from JWT, never from URL
export function useEquiposDocente() {
  return useQuery({
    queryKey: ['equipos', 'mis-equipos'],
    queryFn: getEquiposDocente,
  })
}

// Hook for tenant-wide asignaciones with filters
export function useAsignacionesTenant(filtros: FiltrosAsignaciones = {}) {
  return useQuery({
    queryKey: ['equipos', 'asignaciones', filtros],
    queryFn: () => getAsignacionesTenant(filtros),
  })
}

// Hook for bulk assignment mutation
export function useAsignacionMasiva() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: AsignacionMasivaPayload) => crearAsignacionesMasivas(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['equipos'] })
    },
  })
}

// Hook for clone equipo mutation
export function useClonarEquipo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ClonarEquipoPayload) => clonarEquipo(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['equipos'] })
    },
  })
}

// Hook for modifying vigencia
export function useModificarVigenciaEquipo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ModificarVigenciaPayload) => modificarVigenciaEquipo(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['equipos'] })
    },
  })
}
