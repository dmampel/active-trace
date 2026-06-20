export interface Alumno {
  id: string
  nombre: string
  apellido: string
  email: string
}

export interface AlumnoAtrasado extends Alumno {
  actividadesFaltantes: number
  nota: number
}

export interface AlumnoRanking extends Alumno {
  actividadesAprobadas: number
  nota: number
}

export interface NotaFinal extends Alumno {
  notaFinal: number
}

export interface ReportesMetricas {
  totalAlumnos: number
  porcentajeAlDia: number
  actividadesIncluidas: number
  promedioGeneral: number
}

export interface AlumnoMonitor extends Alumno {
  comision: string
  regional: string
  actividad: string
  actividadesCumplidas: number
}

export interface Umbral {
  valor: number
}

export type AnalisisTab = 'atrasados' | 'ranking' | 'reportes' | 'notas'
