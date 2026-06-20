import { apiClient } from '@/shared/services/api'
import type { MensajeTracking, EnviarComunicacionPayload, PreviewMensaje } from '../types'

export async function enviarComunicacion(payload: EnviarComunicacionPayload): Promise<void> {
  await apiClient.post('/comunicaciones/enviar', payload)
}

export async function getTracking(comisionId: string): Promise<MensajeTracking[]> {
  const res = await apiClient.get<MensajeTracking[]>(`/comunicaciones/${comisionId}/tracking`)
  return res.data
}

export async function getPreviewMensaje(
  comisionId: string,
  alumnoId: string,
): Promise<PreviewMensaje> {
  const res = await apiClient.get<PreviewMensaje>(
    `/comunicaciones/${comisionId}/preview/${alumnoId}`,
  )
  return res.data
}
