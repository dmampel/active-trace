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

interface UsuarioListItemRaw {
  id: string
  email: string
  nombre: string | null
  apellidos: string | null
  regional: string | null
  facturador: boolean
  estado: 'activa' | 'inactiva'
}

function mapUsuario(u: UsuarioListItemRaw): UsuarioResumen {
  return {
    id: u.id,
    nombre: u.nombre ?? '',
    apellido: u.apellidos ?? '',
    email: u.email,
    roles: [],
    activo: u.estado === 'activa',
    modalidadCobro: u.facturador ? 'factura' : 'liquidacion',
    regional: u.regional,
  }
}

export async function getUsuariosAdmin(activo?: boolean): Promise<UsuarioResumen[]> {
  const res = await apiClient.get<UsuarioListItemRaw[]>('/usuarios', {
    params: activo !== undefined ? { activo } : {},
  })
  return res.data.map(mapUsuario)
}

export async function crearUsuario(payload: {
  nombre: string
  apellido: string
  email: string
  password: string
  roles: string[]
  modalidadCobro: 'factura' | 'liquidacion'
}): Promise<UsuarioResumen> {
  const res = await apiClient.post<UsuarioListItemRaw>('/usuarios', {
    email: payload.email,
    password: payload.password,
    nombre: payload.nombre,
    apellidos: payload.apellido,
    facturador: payload.modalidadCobro === 'factura',
  })
  return mapUsuario(res.data)
}

export async function editarUsuario(
  id: string,
  payload: { activo?: boolean; roles?: string[]; modalidadCobro?: string },
): Promise<UsuarioResumen> {
  const backendPayload: Record<string, unknown> = {}
  if (payload.activo !== undefined) {
    backendPayload.estado = payload.activo ? 'activa' : 'inactiva'
  }
  if (payload.modalidadCobro !== undefined) {
    backendPayload.facturador = payload.modalidadCobro === 'factura'
  }
  const res = await apiClient.patch<UsuarioListItemRaw>(`/usuarios/${id}`, backendPayload)
  return mapUsuario(res.data)
}

// ── Auditoría ─────────────────────────────────────────────────────────────────

export async function getPanelAuditoria(filtros: FiltrosAuditoria = {}): Promise<PanelAuditoria> {
  const res = await apiClient.get<PanelAuditoria>('/auditoria/panel', { params: filtros })
  return res.data
}

interface AuditLogEntryRaw {
  id: string
  fecha_hora: string
  actor_id: string
  materia_id: string | null
  accion: string
  filas_afectadas: number | null
  ip: string | null
  user_agent: string | null
}

export async function getLogAuditoria(filtros: FiltrosAuditoria = {}): Promise<AuditLogEntry[]> {
  const res = await apiClient.get<{ items: AuditLogEntryRaw[]; total: number; page: number; page_size: number }>('/auditoria/log', { params: filtros })
  return res.data.items.map((u) => ({
    id: u.id,
    fecha: u.fecha_hora,
    usuarioId: u.actor_id,
    usuarioNombre: u.actor_id.slice(0, 8),
    usuarioApellido: '',
    accion: u.accion,
    materia: u.materia_id,
    filasAfectadas: u.filas_afectadas ?? 0,
    ip: u.ip ?? '',
    userAgent: u.user_agent,
  }))
}
