import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAvisos,
  getAviso,
  crearAviso,
  editarAviso,
  toggleAvisoActivo,
  getConfirmacionesAviso,
} from '../services/avisosApi'
import type { FiltrosAvisos, AvisoFormValues } from '../types'

export function useAvisos(filtros: FiltrosAvisos = {}) {
  return useQuery({
    queryKey: ['avisos', filtros],
    queryFn: () => getAvisos(filtros),
  })
}

export function useAviso(id: string) {
  return useQuery({
    queryKey: ['avisos', id],
    queryFn: () => getAviso(id),
    enabled: !!id,
  })
}

export function useCrearAviso() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AvisoFormValues) => crearAviso(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['avisos'] })
    },
  })
}

export function useEditarAviso(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AvisoFormValues) => editarAviso(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['avisos'] })
    },
  })
}

export function useToggleAvisoActivo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, activo }: { id: string; activo: boolean }) => toggleAvisoActivo(id, activo),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['avisos'] })
    },
  })
}

export function useConfirmacionesAviso(avisoId: string) {
  return useQuery({
    queryKey: ['avisos', avisoId, 'confirmaciones'],
    queryFn: () => getConfirmacionesAviso(avisoId),
    enabled: !!avisoId,
  })
}
