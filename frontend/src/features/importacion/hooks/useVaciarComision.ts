import { useMutation, useQueryClient } from '@tanstack/react-query'
import { vaciarComision } from '../services/importacionApi'

export function useVaciarComision(comisionId: string) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => vaciarComision(comisionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['analisis', comisionId] })
      void queryClient.invalidateQueries({ queryKey: ['comision', comisionId] })
    },
  })

  return {
    vaciar: () => mutation.mutateAsync(),
    isLoading: mutation.isPending,
    error: mutation.isError ? 'Error al vaciar los datos de la comisión.' : null,
    isSuccess: mutation.isSuccess,
  }
}
