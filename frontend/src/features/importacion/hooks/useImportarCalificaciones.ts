import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadCalificaciones, confirmarImportacion } from '../services/importacionApi'
import type { PreviewImportacion, ImportacionPayload } from '../types'

export interface UseImportarCalificacionesResult {
  uploadProgress: number
  preview: PreviewImportacion | null
  uploadError: string | null
  isUploading: boolean
  isConfirming: boolean
  confirmError: string | null
  upload: (comisionId: string, file: File) => Promise<void>
  confirmar: (comisionId: string, payload: ImportacionPayload) => Promise<void>
  reset: () => void
}

export function useImportarCalificaciones(): UseImportarCalificacionesResult {
  const queryClient = useQueryClient()
  const [uploadProgress, setUploadProgress] = useState(0)
  const [preview, setPreview] = useState<PreviewImportacion | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const uploadMutation = useMutation({
    mutationFn: ({ comisionId, file }: { comisionId: string; file: File }) =>
      uploadCalificaciones(comisionId, file, setUploadProgress),
    onSuccess: (data) => {
      setPreview(data)
      setUploadError(null)
    },
    onError: (err: { response?: { status: number } }) => {
      if (err?.response?.status === 413) {
        setUploadError('El archivo supera el tamaño máximo permitido')
      } else {
        setUploadError('Error al subir el archivo. Intentá de nuevo.')
      }
    },
  })

  const confirmMutation = useMutation({
    mutationFn: ({ comisionId, payload }: { comisionId: string; payload: ImportacionPayload }) =>
      confirmarImportacion(comisionId, payload),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['analisis', variables.comisionId] })
      void queryClient.invalidateQueries({ queryKey: ['comision', variables.comisionId] })
    },
  })

  const upload = async (comisionId: string, file: File) => {
    setUploadProgress(0)
    setUploadError(null)
    await uploadMutation.mutateAsync({ comisionId, file })
  }

  const confirmar = async (comisionId: string, payload: ImportacionPayload) => {
    await confirmMutation.mutateAsync({ comisionId, payload })
  }

  const reset = () => {
    setUploadProgress(0)
    setPreview(null)
    setUploadError(null)
    uploadMutation.reset()
    confirmMutation.reset()
  }

  return {
    uploadProgress,
    preview,
    uploadError,
    isUploading: uploadMutation.isPending,
    isConfirming: confirmMutation.isPending,
    confirmError: confirmMutation.error
      ? 'Error al confirmar la importación. Intentá de nuevo.'
      : null,
    upload,
    confirmar,
    reset,
  }
}
