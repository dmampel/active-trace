import { apiClient } from '@/shared/services/api'
import type {
  Asignacion,
  Equipo,
  AsignacionMasivaPayload,
  AsignacionMasivaItem,
  ClonarEquipoPayload,
  ClonarEquipoResult,
  ModificarVigenciaPayload,
  FiltrosAsignaciones,
} from '../types'

export async function getEquiposDocente(): Promise<Equipo[]> {
  const res = await apiClient.get<Equipo[]>('/equipos/mis-equipos')
  return res.data
}

export async function getAsignacionesTenant(filtros: FiltrosAsignaciones = {}): Promise<Asignacion[]> {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.carreraId) params.set('carrera_id', filtros.carreraId)
  if (filtros.cohorteId) params.set('cohorte_id', filtros.cohorteId)
  if (filtros.rol) params.set('rol', filtros.rol)
  if (filtros.docenteNombre) params.set('docente_nombre', filtros.docenteNombre)
  if (filtros.page !== undefined) params.set('page', String(filtros.page))
  if (filtros.pageSize !== undefined) params.set('page_size', String(filtros.pageSize))

  const res = await apiClient.get<Asignacion[]>(`/equipos/asignaciones?${params.toString()}`)
  return res.data
}

export async function crearAsignacionesMasivas(
  payload: AsignacionMasivaPayload,
): Promise<AsignacionMasivaItem[]> {
  const res = await apiClient.post<AsignacionMasivaItem[]>('/equipos/asignaciones/masiva', payload)
  return res.data
}

export async function clonarEquipo(payload: ClonarEquipoPayload): Promise<ClonarEquipoResult> {
  const res = await apiClient.post<ClonarEquipoResult>('/equipos/clonar', payload)
  return res.data
}

export async function modificarVigenciaEquipo(payload: ModificarVigenciaPayload): Promise<void> {
  await apiClient.patch(`/equipos/${payload.equipoId}/vigencia`, {
    vigencia_desde: payload.vigenciaDesde,
    vigencia_hasta: payload.vigenciaHasta,
  })
}

export function exportarEquipoCsvUrl(filtros: FiltrosAsignaciones = {}): string {
  const params = new URLSearchParams()
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.carreraId) params.set('carrera_id', filtros.carreraId)
  if (filtros.cohorteId) params.set('cohorte_id', filtros.cohorteId)
  if (filtros.rol) params.set('rol', filtros.rol)
  if (filtros.docenteNombre) params.set('docente_nombre', filtros.docenteNombre)
  params.set('format', 'csv')
  return `/api/equipos/asignaciones/export?${params.toString()}`
}
