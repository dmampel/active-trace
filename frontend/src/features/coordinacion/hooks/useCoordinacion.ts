import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMonitorGeneral,
  getMonitorSeguimiento,
  getEncuentrosAdmin,
  getGuardias,
  getColoquiosMetricas,
  getConvocatorias,
  crearConvocatoria,
  getReservasConvocatoria,
  getRegistroAcademico,
  importarPadronColoquio,
  getMensajesPendientes,
  aprobarMensaje,
  cancelarMensaje,
  aprobarLote,
} from '../services/coordinacionApi'
import type {
  FiltrosMonitor,
  FiltrosEncuentros,
  FiltrosGuardias,
  CrearConvocatoriaPayload,
} from '../types'

// Monitor general — tenant from JWT
export function useMonitorGeneral(filtros: FiltrosMonitor = {}) {
  return useQuery({
    queryKey: ['coordinacion', 'monitor', filtros],
    queryFn: () => getMonitorGeneral(filtros),
  })
}

// Monitor seguimiento — extends monitor with date range
export function useMonitorSeguimiento(filtros: FiltrosMonitor = {}) {
  return useQuery({
    queryKey: ['coordinacion', 'monitor-seguimiento', filtros],
    queryFn: () => getMonitorSeguimiento(filtros),
  })
}

// Encuentros admin
export function useEncuentrosAdmin(filtros: FiltrosEncuentros = {}) {
  return useQuery({
    queryKey: ['coordinacion', 'encuentros', filtros],
    queryFn: () => getEncuentrosAdmin(filtros),
  })
}

// Guardias
export function useGuardias(filtros: FiltrosGuardias = {}) {
  return useQuery({
    queryKey: ['coordinacion', 'guardias', filtros],
    queryFn: () => getGuardias(filtros),
  })
}

// Coloquios metrics
export function useColoquiosMetricas() {
  return useQuery({
    queryKey: ['coordinacion', 'coloquios', 'metricas'],
    queryFn: getColoquiosMetricas,
  })
}

// Convocatorias list
export function useConvocatorias() {
  return useQuery({
    queryKey: ['coordinacion', 'coloquios', 'convocatorias'],
    queryFn: getConvocatorias,
  })
}

// Create convocatoria
export function useCrearConvocatoria() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CrearConvocatoriaPayload) => crearConvocatoria(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'coloquios'] })
    },
  })
}

// Reservas for a convocatoria
export function useReservasConvocatoria(convocatoriaId: string) {
  return useQuery({
    queryKey: ['coordinacion', 'coloquios', convocatoriaId, 'reservas'],
    queryFn: () => getReservasConvocatoria(convocatoriaId),
    enabled: !!convocatoriaId,
  })
}

// Registro academico
export function useRegistroAcademico(convocatoriaId: string) {
  return useQuery({
    queryKey: ['coordinacion', 'coloquios', convocatoriaId, 'registro'],
    queryFn: () => getRegistroAcademico(convocatoriaId),
    enabled: !!convocatoriaId,
  })
}

// Import padron (multipart)
export function useImportarPadronColoquio(convocatoriaId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => importarPadronColoquio(convocatoriaId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'coloquios', convocatoriaId] })
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'coloquios', 'convocatorias'] })
    },
  })
}

// Aprobacion de comunicaciones — conditional polling
export function useAprobacionComunicaciones() {
  const { data, ...rest } = useQuery({
    queryKey: ['coordinacion', 'comunicaciones', 'pendientes'],
    queryFn: getMensajesPendientes,
    refetchInterval: (query) => {
      const data = query.state.data
      if (Array.isArray(data) && data.length > 0) return 5000
      return false
    },
  })

  return { mensajes: data ?? [], ...rest }
}

// Mutations for comunicaciones
export function useAprobarMensaje() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (mensajeId: string) => aprobarMensaje(mensajeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'comunicaciones'] })
    },
  })
}

export function useCancelarMensaje() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (mensajeId: string) => cancelarMensaje(mensajeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'comunicaciones'] })
    },
  })
}

export function useAprobarLote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (mensajeIds: string[]) => aprobarLote(mensajeIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coordinacion', 'comunicaciones'] })
    },
  })
}
