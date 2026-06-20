// Tipos para el módulo de administración

export interface Carrera {
  id: string
  codigo: string
  nombre: string
  activa: boolean
  creadaEn: string
}

export interface Cohorte {
  id: string
  nombre: string
  anioInicio: number
  desde: string
  hasta: string
  activa: boolean
  carreraId: string
  carreraNombre: string
}

export interface Materia {
  id: string
  codigo: string
  nombre: string
  activa: boolean
  creadaEn: string
}

export interface UsuarioResumen {
  id: string
  nombre: string
  apellido: string
  email: string
  roles: string[]
  activo: boolean
  modalidadCobro: 'factura' | 'liquidacion'
  regional: string | null
}

export interface AuditLogEntry {
  id: string
  fecha: string
  usuarioId: string
  usuarioNombre: string
  usuarioApellido: string
  accion: string
  materia: string | null
  filasAfectadas: number
  ip: string
  userAgent: string | null
}

export interface EstadoComunicacionDocente {
  docenteId: string
  docenteNombre: string
  docenteApellido: string
  pendiente: number
  enviando: number
  enviado: number
  fallido: number
  cancelado: number
}

export interface PanelAuditoria {
  accionesPorDia: { fecha: string; total: number }[]
  estadoComunicaciones: EstadoComunicacionDocente[]
  ultimasAcciones: AuditLogEntry[]
}

export interface FiltrosAuditoria {
  desde?: string
  hasta?: string
  materia?: string
  usuario?: string
  estado?: string
}
