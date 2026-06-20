export type EstadoEncuentro = 'programado' | 'en_curso' | 'realizado' | 'cancelado'
export type EstadoGuardia = 'pendiente' | 'cubierta' | 'ausente'

export interface Encuentro {
  id: string
  materiaId: string
  materiaNombre: string
  docenteId: string
  docenteNombre: string
  docenteApellido: string
  fecha: string
  horaInicio: string
  horaFin: string
  estado: EstadoEncuentro
  grabacionUrl: string | null
  descripcion: string
}

export interface Guardia {
  id: string
  tutorId: string
  tutorNombre: string
  tutorApellido: string
  materiaId: string
  materiaNombre: string
  carreraId: string
  carreraNombre: string
  cohorteId: string
  cohorteNombre: string
  dia: string
  horario: string
  estado: EstadoGuardia
  comentarios: string
}

export type EstadoReserva = 'activa' | 'cancelada' | 'completada'
export type ResultadoColoquio = 'aprobado' | 'desaprobado' | 'ausente'

export interface Convocatoria {
  id: string
  materiaId: string
  materiaNombre: string
  instanciaNombre: string
  diasDisponibles: string[]
  cuposPorDia: number
  totalAlumnosConvocados: number
  reservasActivas: number
  notasRegistradas: number
  activa: boolean
  creadaEn: string
}

export interface ReservaColoquio {
  id: string
  convocatoriaId: string
  alumnoId: string
  alumnoNombre: string
  alumnoApellido: string
  alumnoEmail: string
  dia: string
  cupo: number
  estado: EstadoReserva
}

export interface RegistroAcademico {
  alumnoId: string
  alumnoNombre: string
  alumnoApellido: string
  nota: number | null
  resultado: ResultadoColoquio | null
}

export interface ColoquiosMetricas {
  totalAlumnosCargados: number
  instanciasActivas: number
  reservasActivas: number
  notasRegistradas: number
}

export interface FiltrosMonitor {
  materiaId?: string
  regional?: string
  comision?: string
  estado?: string
  alumno?: string
  fechaDesde?: string
  fechaHasta?: string
  page?: number
  pageSize?: number
}

export interface AlumnoMonitorGeneral {
  alumnoId: string
  alumnoNombre: string
  alumnoApellido: string
  email: string
  materia: string
  comision: string
  regional: string
  estado: string
  actividadesCumplidas: number
  actividadesTotales: number
}

export interface FiltrosEncuentros {
  materiaId?: string
  docenteId?: string
  estado?: EstadoEncuentro
}

export interface FiltrosGuardias {
  materiaId?: string
  tutorId?: string
  estado?: EstadoGuardia
}

export interface CrearConvocatoriaPayload {
  materiaId: string
  instanciaNombre: string
  diasDisponibles: string[]
  cuposPorDia: number
}

export interface MensajePendiente {
  id: string
  asunto: string
  destinatarioNombre: string
  destinatarioApellido: string
  destinatarioEmail: string
  emisorNombre: string
  emisorApellido: string
  creadoEn: string
  estado: 'pendiente' | 'enviando' | 'enviado' | 'cancelado'
}
