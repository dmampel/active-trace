import { apiClient } from '@/shared/services/api'
import type {
  Liquidacion,
  SalarioBase,
  SalarioPlus,
  Factura,
  FiltrosFacturas,
} from '../types'

// ── Liquidaciones ─────────────────────────────────────────────────────────────

export async function getLiquidaciones(periodo: string): Promise<Liquidacion[]> {
  const res = await apiClient.get<Liquidacion[]>('/liquidaciones', { params: { periodo } })
  return res.data
}

export async function cerrarLiquidacion(periodo: string): Promise<void> {
  await api.post('/liquidaciones/cerrar', { periodo })
}

export async function getHistorialLiquidaciones(): Promise<Liquidacion[]> {
  const res = await apiClient.get<Liquidacion[]>('/liquidaciones/historial')
  return res.data
}

// ── Salarios base ─────────────────────────────────────────────────────────────

export async function getSalariosBase(): Promise<SalarioBase[]> {
  const res = await apiClient.get<SalarioBase[]>('/salarios/base')
  return res.data
}

export async function crearSalarioBase(payload: {
  rol: string
  monto: number
  desde: string
  hasta: string | null
}): Promise<SalarioBase> {
  const res = await apiClient.post<SalarioBase>('/salarios/base', payload)
  return res.data
}

export async function eliminarSalarioBase(id: string): Promise<void> {
  await api.delete(`/salarios/base/${id}`)
}

// ── Salarios plus ─────────────────────────────────────────────────────────────

export async function getSalariosPlus(): Promise<SalarioPlus[]> {
  const res = await apiClient.get<SalarioPlus[]>('/salarios/plus')
  return res.data
}

export async function crearSalarioPlus(payload: {
  clave: string
  rol: string
  descripcion: string
  monto: number
  desde: string
  hasta: string | null
}): Promise<SalarioPlus> {
  const res = await apiClient.post<SalarioPlus>('/salarios/plus', payload)
  return res.data
}

export async function eliminarSalarioPlus(id: string): Promise<void> {
  await api.delete(`/salarios/plus/${id}`)
}

// ── Facturas ──────────────────────────────────────────────────────────────────

export async function getFacturas(filtros: FiltrosFacturas = {}): Promise<Factura[]> {
  const res = await apiClient.get<Factura[]>('/facturas', { params: filtros })
  return res.data
}

export async function marcarFacturaAbonada(id: string): Promise<Factura> {
  const res = await apiClient.patch<Factura>(`/facturas/${id}/estado`, { estado: 'abonada' })
  return res.data
}
