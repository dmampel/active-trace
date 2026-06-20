import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getLiquidaciones,
  cerrarLiquidacion,
  getHistorialLiquidaciones,
  getSalariosBase,
  crearSalarioBase,
  eliminarSalarioBase,
  getSalariosPlus,
  crearSalarioPlus,
  eliminarSalarioPlus,
  getFacturas,
  marcarFacturaAbonada,
} from '../services/liquidacionesApi'
import type { FiltrosFacturas, SalarioBase, SalarioPlus } from '../types'

// ── Liquidaciones ─────────────────────────────────────────────────────────────

export function useLiquidaciones(periodo: string) {
  return useQuery({
    queryKey: ['liquidaciones', 'periodo', periodo],
    queryFn: () => getLiquidaciones(periodo),
    enabled: !!periodo,
  })
}

export function useCerrarLiquidacion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (periodo: string) => cerrarLiquidacion(periodo),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['liquidaciones'] })
    },
  })
}

export function useHistorialLiquidaciones() {
  return useQuery({
    queryKey: ['liquidaciones', 'historial'],
    queryFn: getHistorialLiquidaciones,
  })
}

// ── Grilla salarial ───────────────────────────────────────────────────────────

export function useSalariosBase() {
  return useQuery({
    queryKey: ['salarios', 'base'],
    queryFn: getSalariosBase,
  })
}

export function useCrearSalarioBase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Omit<SalarioBase, 'id'>) => crearSalarioBase(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['salarios', 'base'] })
    },
  })
}

export function useEliminarSalarioBase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => eliminarSalarioBase(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['salarios', 'base'] })
    },
  })
}

export function useSalariosPlus() {
  return useQuery({
    queryKey: ['salarios', 'plus'],
    queryFn: getSalariosPlus,
  })
}

export function useCrearSalarioPlus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Omit<SalarioPlus, 'id'>) => crearSalarioPlus(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['salarios', 'plus'] })
    },
  })
}

export function useEliminarSalarioPlus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => eliminarSalarioPlus(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['salarios', 'plus'] })
    },
  })
}

// ── Facturas ──────────────────────────────────────────────────────────────────

export function useFacturas(filtros: FiltrosFacturas = {}) {
  return useQuery({
    queryKey: ['facturas', filtros],
    queryFn: () => getFacturas(filtros),
  })
}

export function useMarcarFacturaAbonada() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => marcarFacturaAbonada(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['facturas'] })
    },
  })
}
