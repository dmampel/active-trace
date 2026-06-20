import { useMutation } from '@tanstack/react-query'
import { uploadFinalizacion } from '../services/importacionApi'
import type { FinalizacionItem } from '../types'

export interface UseFinalizacionActividadesResult {
  items: FinalizacionItem[]
  isLoading: boolean
  error: string | null
  upload: (comisionId: string, file: File) => Promise<void>
}

export function useFinalizacionActividades(): UseFinalizacionActividadesResult {
  const mutation = useMutation({
    mutationFn: ({ comisionId, file }: { comisionId: string; file: File }) =>
      uploadFinalizacion(comisionId, file),
  })

  const upload = async (comisionId: string, file: File) => {
    await mutation.mutateAsync({ comisionId, file })
  }

  return {
    items: mutation.data?.items ?? [],
    isLoading: mutation.isPending,
    error: mutation.isError ? 'Error al procesar el reporte de finalización.' : null,
    upload,
  }
}
