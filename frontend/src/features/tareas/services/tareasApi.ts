import { apiClient } from '@/shared/services/api'
import type {
  Tarea,
  ComentarioTarea,
  FiltrosTareas,
  AgregarComentarioPayload,
  CambiarEstadoPayload,
} from '../types'

export async function getMisTareas(): Promise<Tarea[]> {
  const res = await apiClient.get<Tarea[]>('/tareas/mis-tareas')
  return res.data
}

export async function getAdminTareas(filtros: FiltrosTareas = {}): Promise<Tarea[]> {
  const params = new URLSearchParams()
  if (filtros.estado) params.set('estado', filtros.estado)
  if (filtros.docenteId) params.set('docente_id', filtros.docenteId)
  if (filtros.materiaId) params.set('materia_id', filtros.materiaId)
  if (filtros.asignadoPorId) params.set('asignado_por_id', filtros.asignadoPorId)
  if (filtros.page !== undefined) params.set('page', String(filtros.page))
  if (filtros.pageSize !== undefined) params.set('page_size', String(filtros.pageSize))

  const res = await apiClient.get<Tarea[]>(`/tareas?${params.toString()}`)
  return res.data
}

export async function agregarComentario(
  tareaId: string,
  payload: AgregarComentarioPayload,
): Promise<ComentarioTarea> {
  const res = await apiClient.post<ComentarioTarea>(`/tareas/${tareaId}/comentarios`, payload)
  return res.data
}

export async function cambiarEstadoTarea(
  tareaId: string,
  payload: CambiarEstadoPayload,
): Promise<Tarea> {
  const res = await apiClient.patch<Tarea>(`/tareas/${tareaId}/estado`, payload)
  return res.data
}
