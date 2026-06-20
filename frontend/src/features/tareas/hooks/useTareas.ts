import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMisTareas,
  getAdminTareas,
  agregarComentario,
  cambiarEstadoTarea,
} from '../services/tareasApi'
import type {
  FiltrosTareas,
  AgregarComentarioPayload,
  CambiarEstadoPayload,
} from '../types'

// Scoped to authenticated user — identity from JWT
export function useMisTareas() {
  return useQuery({
    queryKey: ['tareas', 'mis-tareas'],
    queryFn: getMisTareas,
  })
}

// Admin view with filters
export function useAdminTareas(filtros: FiltrosTareas = {}) {
  return useQuery({
    queryKey: ['tareas', 'admin', filtros],
    queryFn: () => getAdminTareas(filtros),
  })
}

export function useAgregarComentario(tareaId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: AgregarComentarioPayload) => agregarComentario(tareaId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tareas'] })
    },
  })
}

export function useCambiarEstadoTarea() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tareaId, payload }: { tareaId: string; payload: CambiarEstadoPayload }) =>
      cambiarEstadoTarea(tareaId, payload),
    // Optimistic update
    onMutate: async ({ tareaId, payload }) => {
      await queryClient.cancelQueries({ queryKey: ['tareas'] })
      const previous = queryClient.getQueryData(['tareas', 'mis-tareas'])
      queryClient.setQueryData(['tareas', 'mis-tareas'], (old: unknown) => {
        if (!Array.isArray(old)) return old
        return old.map((t: { id: string; estado: string }) =>
          t.id === tareaId ? { ...t, estado: payload.estado } : t,
        )
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['tareas', 'mis-tareas'], context.previous)
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['tareas'] })
    },
  })
}
