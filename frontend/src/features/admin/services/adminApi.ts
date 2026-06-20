import { apiClient } from '@/shared/services/api'
import type { Carrera, Cohorte, Materia, UsuarioResumen, PanelAuditoria, AuditLogEntry, FiltrosAuditoria } from '../types'

// ── Carreras ──────────────────────────────────────────────────────────────────

export async function getCarreras(): Promise<Carrera[]> {
  const res = await apiClient.get<Carrera[]>('/estructura/carreras')
  return res.data
}

export async function crearCarrera(payload: { codigo: string; nombre: string }): Promise<Carrera> {
  const res = await apiClient.post<Carrera>('/estructura/carreras', payload)
  return res.data
}

export async function editarCarrera(
  id: string,
  payload: { nombre?: string; activa?: boolean },
): Promise<Carrera> {
  const res = await apiClient.patch<Carrera>(`/estructura/carreras/${id}`, payload)
  return res.data
}

// ── Cohortes ──────────────────────────────────────────────────────────────────

export async function getCohortes(): Promise<Cohorte[]> {
  const res = await apiClient.get<Cohorte[]>('/estructura/cohortes')
  return res.data
}

export async function crearCohorte(payload: {
  nombre: string
  anioInicio: number
  desde: string
  hasta: string
  carreraId: string
}): Promise<Cohorte> {
  const res = await apiClient.post<Cohorte>('/estructura/cohortes', payload)
  return res.data
}

export async function editarCohorte(
  id: string,
  payload: { nombre?: string; desde?: string; hasta?: string; activa?: boolean },
): Promise<Cohorte> {
  const res = await apiClient.patch<Cohorte>(`/estructura/cohortes/${id}`, payload)
  return res.data
}

// ── Materias ──────────────────────────────────────────────────────────────────

export async function getMaterias(): Promise<Materia[]> {
  const res = await apiClient.get<Materia[]>('/estructura/materias')
  return res.data
}

export async function crearMateria(payload: { codigo: string; nombre: string }): Promise<Materia> {
  const res = await apiClient.post<Materia>('/estructura/materias', payload)
  return res.data
}

export async function editarMateria(
  id: string,
  payload: { nombre?: string; activa?: boolean },
): Promise<Materia> {
  const res = await apiClient.patch<Materia>(`/estructura/materias/${id}`, payload)
  return res.data
}

// ── Usuarios ──────────────────────────────────────────────────────────────────

export async function getUsuariosAdmin(activo?: boolean): Promise<UsuarioResumen[]> {
  const res = await apiClient.get<UsuarioResumen[]>('/admin/usuarios', {
    params: activo !== undefined ? { activo } : {},
  })
  return res.data
}

export async function crearUsuario(payload: {
  nombre: string
  apellido: string
  email: string
  roles: string[]
  modalidadCobro: 'factura' | 'liquidacion'
}): Promise<UsuarioResumen> {
  const res = await apiClient.post<UsuarioResumen>('/admin/usuarios', payload)
  return res.data
}

export async function editarUsuario(
  id: string,
  payload: { activo?: boolean; roles?: string[]; modalidadCobro?: string },
): Promise<UsuarioResumen> {
  const res = await apiClient.patch<UsuarioResumen>(`/admin/usuarios/${id}`, payload)
  return res.data
}

// ── Auditoría ─────────────────────────────────────────────────────────────────

export async function getPanelAuditoria(filtros: FiltrosAuditoria = {}): Promise<PanelAuditoria> {
  const res = await apiClient.get<PanelAuditoria>('/auditoria/panel', { params: filtros })
  return res.data
}

export async function getLogAuditoria(filtros: FiltrosAuditoria = {}): Promise<AuditLogEntry[]> {
  const res = await apiClient.get<AuditLogEntry[]>('/auditoria/log', { params: filtros })
  return res.data
}
