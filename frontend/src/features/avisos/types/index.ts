export type AvisoScope = 'global' | 'materia' | 'cohorte'
export type AvisoSeveridad = 'info' | 'advertencia' | 'critico'
export type AvisoRol = 'PROFESOR' | 'TUTOR' | 'NEXO' | 'COORDINADOR' | 'ADMIN' | 'ALUMNO'

export interface Aviso {
  id: string
  scope: AvisoScope
  roles: AvisoRol[]
  severidad: AvisoSeveridad
  titulo: string
  cuerpo: string
  vigenciaDesde: string
  vigenciaHasta: string | null
  orden: number
  requireAck: boolean
  activo: boolean
  materiaId?: string
  materiaNombre?: string
  cohorteId?: string
  cohorteNombre?: string
  creadoPor: string
  creadoEn: string
}

export interface ConfirmacionAviso {
  id: string
  avisoId: string
  userId: string
  userNombre: string
  userApellido: string
  userEmail: string
  confirmedAt: string
}

export interface AvisoFormValues {
  scope: AvisoScope
  roles: AvisoRol[]
  severidad: AvisoSeveridad
  titulo: string
  cuerpo: string
  vigenciaDesde: string
  vigenciaHasta?: string
  orden: number
  requireAck: boolean
  materiaId?: string
  cohorteId?: string
}

export interface FiltrosAvisos {
  activo?: boolean
  scope?: AvisoScope
}
