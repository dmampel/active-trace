import { apiClient } from '@/shared/services/api'
import type {
  Aviso,
  AvisoFormValues,
  ConfirmacionAviso,
  FiltrosAvisos,
} from '../types'

export async function getAvisos(filtros: FiltrosAvisos = {}): Promise<Aviso[]> {
  const params = new URLSearchParams()
  if (filtros.activo !== undefined) params.set('activo', String(filtros.activo))
  if (filtros.scope) params.set('scope', filtros.scope)

  const res = await apiClient.get<Aviso[]>(`/avisos?${params.toString()}`)
  return res.data
}

export async function getAviso(id: string): Promise<Aviso> {
  const res = await apiClient.get<Aviso>(`/avisos/${id}`)
  return res.data
}

export async function crearAviso(data: AvisoFormValues): Promise<Aviso> {
  const res = await apiClient.post<Aviso>('/avisos', data)
  return res.data
}

export async function editarAviso(id: string, data: AvisoFormValues): Promise<Aviso> {
  const res = await apiClient.put<Aviso>(`/avisos/${id}`, data)
  return res.data
}

export async function toggleAvisoActivo(id: string, activo: boolean): Promise<Aviso> {
  const res = await apiClient.patch<Aviso>(`/avisos/${id}/activo`, { activo })
  return res.data
}

export async function getConfirmacionesAviso(avisoId: string): Promise<ConfirmacionAviso[]> {
  const res = await apiClient.get<ConfirmacionAviso[]>(`/avisos/${avisoId}/confirmaciones`)
  return res.data
}
