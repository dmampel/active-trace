export type RolEquipo = 'PROFESOR' | 'TUTOR' | 'NEXO' | 'COORDINADOR'
export type EstadoAsignacion = 'activa' | 'inactiva' | 'vencida'

export interface Asignacion {
  id: string
  docenteId: string
  docenteNombre: string
  docenteApellido: string
  materiaId: string
  materiaNombre: string
  carreraId: string
  carreraNombre: string
  cohorteId: string
  cohorteNombre: string
  rol: RolEquipo
  vigenciaDesde: string
  vigenciaHasta: string | null
  estado: EstadoAsignacion
}

export interface Equipo {
  id: string
  materiaId: string
  materiaNombre: string
  carreraId: string
  carreraNombre: string
  cohorteId: string
  cohorteNombre: string
  asignaciones: Asignacion[]
}

export interface AsignacionMasivaItem {
  docenteId: string
  resultado: 'ok' | 'error'
  mensaje?: string
}

export interface AsignacionMasivaPayload {
  docenteIds: string[]
  materiaId: string
  carreraId: string
  cohorteId: string
  rol: RolEquipo
  vigenciaDesde: string
  vigenciaHasta?: string
}

export interface ClonarEquipoPayload {
  origenMateriaId: string
  origenCarreraId: string
  origenCohorteId: string
  destinoMateriaId: string
  destinoCarreraId: string
  destinoCohorteId: string
}

export interface ClonarEquipoResult {
  asignacionesCreadas: number
  detalle: Asignacion[]
}

export interface ModificarVigenciaPayload {
  equipoId: string
  vigenciaDesde: string
  vigenciaHasta?: string
}

export interface FiltrosAsignaciones {
  materiaId?: string
  carreraId?: string
  cohorteId?: string
  rol?: RolEquipo
  docenteNombre?: string
  page?: number
  pageSize?: number
}
