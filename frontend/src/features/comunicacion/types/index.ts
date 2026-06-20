export type MensajeEstado = 'Pendiente' | 'Enviando' | 'OK' | 'Fallido' | 'Cancelado'

export const ESTADOS_FINALES: MensajeEstado[] = ['OK', 'Fallido', 'Cancelado']

export interface MensajeTracking {
  id: string
  destinatarioNombre: string
  destinatarioEmail: string
  estado: MensajeEstado
  timestamp: string
}

export interface DestinatarioPayload {
  alumnoId: string
  nombre: string
  email: string
}

export interface EnviarComunicacionPayload {
  comisionId: string
  destinatarios: DestinatarioPayload[]
}

export interface PreviewMensaje {
  asunto: string
  cuerpo: string
}
