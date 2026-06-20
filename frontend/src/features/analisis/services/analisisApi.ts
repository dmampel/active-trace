import { apiClient } from '@/shared/services/api'
import type {
  AlumnoAtrasado,
  AlumnoRanking,
  NotaFinal,
  ReportesMetricas,
  AlumnoMonitor,
  Umbral,
} from '../types'

export async function getAtrasados(comisionId: string): Promise<AlumnoAtrasado[]> {
  const res = await apiClient.get<AlumnoAtrasado[]>(`/comisiones/${comisionId}/analisis/atrasados`)
  return res.data
}

export async function getRanking(comisionId: string): Promise<AlumnoRanking[]> {
  const res = await apiClient.get<AlumnoRanking[]>(`/comisiones/${comisionId}/analisis/ranking`)
  return res.data
}

export async function getNotasFinales(comisionId: string): Promise<NotaFinal[]> {
  const res = await apiClient.get<NotaFinal[]>(`/comisiones/${comisionId}/analisis/notas`)
  return res.data
}

export async function getReportes(comisionId: string): Promise<ReportesMetricas> {
  const res = await apiClient.get<ReportesMetricas>(`/comisiones/${comisionId}/analisis/reportes`)
  return res.data
}

export async function getUmbral(comisionId: string): Promise<Umbral> {
  const res = await apiClient.get<Umbral>(`/comisiones/${comisionId}/analisis/umbral`)
  return res.data
}

export async function updateUmbral(comisionId: string, valor: number): Promise<Umbral> {
  const res = await apiClient.put<Umbral>(`/comisiones/${comisionId}/analisis/umbral`, { valor })
  return res.data
}

export interface MonitorFiltros {
  alumno?: string
  comision?: string
  regional?: string
  actividad?: string
  minimoActividades?: number
}

export async function getMonitorDocente(
  comisionId: string,
  filtros: MonitorFiltros = {},
): Promise<AlumnoMonitor[]> {
  const params = new URLSearchParams()
  if (filtros.alumno) params.set('alumno', filtros.alumno)
  if (filtros.comision) params.set('comision', filtros.comision)
  if (filtros.regional) params.set('regional', filtros.regional)
  if (filtros.actividad) params.set('actividad', filtros.actividad)
  if (filtros.minimoActividades !== undefined)
    params.set('minimo_actividades', String(filtros.minimoActividades))

  const res = await apiClient.get<AlumnoMonitor[]>(
    `/comisiones/${comisionId}/monitor?${params.toString()}`,
  )
  return res.data
}
