import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAtrasados,
  getRanking,
  getNotasFinales,
  getReportes,
  getUmbral,
  updateUmbral,
} from '../services/analisisApi'

export function useAtrasados(comisionId: string) {
  return useQuery({
    queryKey: ['analisis', comisionId, 'atrasados'],
    queryFn: () => getAtrasados(comisionId),
    enabled: !!comisionId,
  })
}

export function useRanking(comisionId: string) {
  return useQuery({
    queryKey: ['analisis', comisionId, 'ranking'],
    queryFn: () => getRanking(comisionId),
    enabled: !!comisionId,
  })
}

export function useNotasFinales(comisionId: string) {
  return useQuery({
    queryKey: ['analisis', comisionId, 'notas'],
    queryFn: () => getNotasFinales(comisionId),
    enabled: !!comisionId,
  })
}

export function useReportes(comisionId: string) {
  return useQuery({
    queryKey: ['analisis', comisionId, 'reportes'],
    queryFn: () => getReportes(comisionId),
    enabled: !!comisionId,
  })
}

export function useUmbral(comisionId: string) {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['analisis', comisionId, 'umbral'],
    queryFn: () => getUmbral(comisionId),
    enabled: !!comisionId,
  })

  const mutation = useMutation({
    mutationFn: (valor: number) => updateUmbral(comisionId, valor),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['analisis', comisionId] })
    },
  })

  return {
    umbral: query.data?.valor,
    isLoading: query.isLoading,
    updateUmbral: (valor: number) => mutation.mutateAsync(valor),
    isUpdating: mutation.isPending,
  }
}
