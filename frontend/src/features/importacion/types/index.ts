export interface Actividad {
  id: string
  nombre: string
  tipo: string
}

export interface ActividadConCalificacion extends Actividad {
  calificacion: number | null
}

export interface PreviewImportacion {
  actividades: Actividad[]
}

export interface ImportacionPayload {
  actividadesIds: string[]
  umbral: number
}

export interface ImportacionResult {
  ok: boolean
  mensaje?: string
}

export interface FinalizacionItem {
  alumnoNombre: string
  alumnoEmail: string
  actividad: string
  estado: string
}

export type WizardStep = 1 | 2 | 3 | 4
