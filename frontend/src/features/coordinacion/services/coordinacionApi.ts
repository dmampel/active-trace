import { apiClient } from '@/shared/services/api'
import type {
  AlumnoMonitorGeneral,
  FiltrosMonitor,
  Encuentro,
  Guardia,
  FiltrosEncuentros,
  FiltrosGuardias,
  Convocatoria,
  ReservaColoquio,
  RegistroAcademico,
  ColoquiosMetricas,
  CrearConvocatoriaPayload,
  MensajePendiente,
} from '../types'

// Monitor general
export async function getMonitorGeneral(filtros: FiltrosMonitor = {}): Promise<AlumnoMonitorGeneral[]> {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.regional) params.set('regional', filtros.regional)
  if (filtros.comision) params.set('comision', filtros.comision)
  if (filtros.estado) params.set('estado', filtros.estado)
  if (filtros.alumno) params.set('alumno', filtros.alumno)
  if (filtros.page !== undefined) params.set('page', String(filtros.page))
  if (filtros.pageSize !== undefined) params.set('page_size', String(filtros.pageSize))

  const res = await apiClient.get<AlumnoMonitorGeneral[]>(`/monitor?${params.toString()}`)
  return res.data
}

export function exportarMonitorCsvUrl(filtros: FiltrosMonitor = {}): string {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.regional) params.set('regional', filtros.regional)
  if (filtros.comision) params.set('comision', filtros.comision)
  if (filtros.estado) params.set('estado', filtros.estado)
  params.set('format', 'csv')
  return `/api/monitor/export?${params.toString()}`
}

// Monitor seguimiento
export async function getMonitorSeguimiento(filtros: FiltrosMonitor = {}): Promise<AlumnoMonitorGeneral[]> {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.regional) params.set('regional', filtros.regional)
  if (filtros.comision) params.set('comision', filtros.comision)
  if (filtros.estado) params.set('estado', filtros.estado)
  if (filtros.alumno) params.set('alumno', filtros.alumno)
  if (filtros.fechaDesde) params.set('fecha_desde', filtros.fechaDesde)
  if (filtros.fechaHasta) params.set('fecha_hasta', filtros.fechaHasta)

  const res = await apiClient.get<AlumnoMonitorGeneral[]>(`/monitor/seguimiento?${params.toString()}`)
  return res.data
}

// Encuentros
export async function getEncuentrosAdmin(filtros: FiltrosEncuentros = {}): Promise<Encuentro[]> {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.docenteId) params.set('docente_id', filtros.docenteId)
  if (filtros.estado) params.set('estado', filtros.estado)

  const res = await apiClient.get<Encuentro[]>(`/encuentros?${params.toString()}`)
  return res.data
}

export async function getGuardias(filtros: FiltrosGuardias = {}): Promise<Guardia[]> {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.tutorId) params.set('tutor_id', filtros.tutorId)
  if (filtros.estado) params.set('estado', filtros.estado)

  const res = await apiClient.get<Guardia[]>(`/guardias?${params.toString()}`)
  return res.data
}

export function exportarGuardiasCsvUrl(filtros: FiltrosGuardias = {}): string {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.tutorId) params.set('tutor_id', filtros.tutorId)
  if (filtros.estado) params.set('estado', filtros.estado)
  params.set('format', 'csv')
  return `/api/guardias/export?${params.toString()}`
}

// Coloquios
export async function getColoquiosMetricas(): Promise<ColoquiosMetricas> {
  const res = await apiClient.get<ColoquiosMetricas>('/coloquios/metricas')
  return res.data
}

export async function getConvocatorias(): Promise<Convocatoria[]> {
  const res = await apiClient.get<Convocatoria[]>('/coloquios/convocatorias')
  return res.data
}

export async function crearConvocatoria(payload: CrearConvocatoriaPayload): Promise<Convocatoria> {
  const res = await apiClient.post<Convocatoria>('/coloquios/convocatorias', payload)
  return res.data
}

export async function getReservasConvocatoria(convocatoriaId: string): Promise<ReservaColoquio[]> {
  const res = await apiClient.get<ReservaColoquio[]>(`/coloquios/convocatorias/${convocatoriaId}/reservas`)
  return res.data
}

export async function getRegistroAcademico(convocatoriaId: string): Promise<RegistroAcademico[]> {
  const res = await apiClient.get<RegistroAcademico[]>(
    `/coloquios/convocatorias/${convocatoriaId}/registro`,
  )
  return res.data
}

export async function importarPadronColoquio(
  convocatoriaId: string,
  file: File,
): Promise<{ importados: number }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiClient.post<{ importados: number }>(
    `/coloquios/convocatorias/${convocatoriaId}/padron`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return res.data
}

// Aprobación de comunicaciones
export async function getMensajesPendientes(): Promise<MensajePendiente[]> {
  const res = await apiClient.get<MensajePendiente[]>('/comunicaciones/pendientes')
  return res.data
}

export async function aprobarMensaje(mensajeId: string): Promise<void> {
  await apiClient.post(`/comunicaciones/${mensajeId}/aprobar`)
}

export async function cancelarMensaje(mensajeId: string): Promise<void> {
  await apiClient.post(`/comunicaciones/${mensajeId}/cancelar`)
}

export async function aprobarLote(mensajeIds: string[]): Promise<void> {
  await apiClient.post('/comunicaciones/aprobar-lote', { ids: mensajeIds })
}
