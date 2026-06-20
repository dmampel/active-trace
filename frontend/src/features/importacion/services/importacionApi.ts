import { apiClient } from '@/shared/services/api'
import type { PreviewImportacion, ImportacionPayload, ImportacionResult } from '../types'

export async function uploadCalificaciones(
  comisionId: string,
  file: File,
  onUploadProgress?: (pct: number) => void,
): Promise<PreviewImportacion> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<PreviewImportacion>(
    `/comisiones/${comisionId}/calificaciones/preview`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onUploadProgress
        ? (e) => {
            if (e.total) onUploadProgress(Math.round((e.loaded * 100) / e.total))
          }
        : undefined,
    },
  )
  return response.data
}

export async function confirmarImportacion(
  comisionId: string,
  payload: ImportacionPayload,
): Promise<ImportacionResult> {
  const response = await apiClient.post<ImportacionResult>(
    `/comisiones/${comisionId}/calificaciones/importar`,
    payload,
  )
  return response.data
}

export async function uploadFinalizacion(comisionId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<{ items: import('../types').FinalizacionItem[] }>(
    `/comisiones/${comisionId}/calificaciones/finalizacion`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return response.data
}

export async function vaciarComision(comisionId: string): Promise<void> {
  await apiClient.delete(`/comisiones/${comisionId}/calificaciones`)
}
