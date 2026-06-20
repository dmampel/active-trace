import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCarreras,
  crearCarrera,
  editarCarrera,
  getCohortes,
  crearCohorte,
  editarCohorte,
  getMaterias,
  crearMateria,
  editarMateria,
  getUsuariosAdmin,
  crearUsuario,
  editarUsuario,
  getPanelAuditoria,
  getLogAuditoria,
} from '../services/adminApi'
import type { FiltrosAuditoria, UsuarioResumen } from '../types'

// ── Carreras ──────────────────────────────────────────────────────────────────

export function useCarreras() {
  return useQuery({ queryKey: ['admin', 'carreras'], queryFn: getCarreras })
}

export function useCrearCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { codigo: string; nombre: string }) => crearCarrera(payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'carreras'] }) },
  })
}

export function useEditarCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { nombre?: string; activa?: boolean } }) =>
      editarCarrera(id, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'carreras'] }) },
  })
}

// ── Cohortes ──────────────────────────────────────────────────────────────────

export function useCohortes() {
  return useQuery({ queryKey: ['admin', 'cohortes'], queryFn: getCohortes })
}

export function useCrearCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { nombre: string; anioInicio: number; desde: string; hasta: string; carreraId: string }) =>
      crearCohorte(payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'cohortes'] }) },
  })
}

export function useEditarCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { nombre?: string; desde?: string; hasta?: string; activa?: boolean } }) =>
      editarCohorte(id, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'cohortes'] }) },
  })
}

// ── Materias ──────────────────────────────────────────────────────────────────

export function useMaterias() {
  return useQuery({ queryKey: ['admin', 'materias'], queryFn: getMaterias })
}

export function useCrearMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { codigo: string; nombre: string }) => crearMateria(payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'materias'] }) },
  })
}

export function useEditarMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { nombre?: string; activa?: boolean } }) =>
      editarMateria(id, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'materias'] }) },
  })
}

// ── Usuarios ──────────────────────────────────────────────────────────────────

export function useUsuariosAdmin(activo?: boolean) {
  return useQuery({
    queryKey: ['admin', 'usuarios', activo],
    queryFn: () => getUsuariosAdmin(activo),
  })
}

export function useCrearUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Omit<UsuarioResumen, 'id' | 'activo' | 'regional'> & { modalidadCobro: 'factura' | 'liquidacion' }) =>
      crearUsuario(payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'usuarios'] }) },
  })
}

export function useEditarUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { activo?: boolean; roles?: string[]; modalidadCobro?: string } }) =>
      editarUsuario(id, payload),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['admin', 'usuarios'] }) },
  })
}

// ── Auditoría ─────────────────────────────────────────────────────────────────

export function usePanelAuditoria(filtros: FiltrosAuditoria = {}) {
  return useQuery({
    queryKey: ['auditoria', 'panel', filtros],
    queryFn: () => getPanelAuditoria(filtros),
  })
}

export function useLogAuditoria(filtros: FiltrosAuditoria = {}) {
  return useQuery({
    queryKey: ['auditoria', 'log', filtros],
    queryFn: () => getLogAuditoria(filtros),
  })
}
