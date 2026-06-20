// Tipos para el módulo de liquidaciones

export type EstadoLiquidacion = 'abierta' | 'cerrada'
export type EstadoFactura = 'pendiente' | 'abonada'
export type ModalidadCobro = 'factura' | 'liquidacion'

export interface Liquidacion {
  id: string
  docente: {
    id: string
    nombre: string
    apellido: string
    rol: string
  }
  periodo: string // 'YYYY-MM'
  salarioBase: number
  plus: number
  total: number
  esNexo: boolean
  excluidoPorFactura: boolean
  estado: EstadoLiquidacion
  creadaEn: string
}

export interface SalarioBase {
  id: string
  rol: string
  monto: number
  desde: string
  hasta: string | null
}

export interface SalarioPlus {
  id: string
  clave: string
  rol: string
  descripcion: string
  monto: number
  desde: string
  hasta: string | null
}

export interface Factura {
  id: string
  docenteId: string
  docenteNombre: string
  docenteApellido: string
  periodo: string
  detalle: string
  estado: EstadoFactura
  archivoUrl: string | null
  archivoBytesSize: number | null
  cargadaEn: string
  pagadaEn: string | null
}

export interface FiltrosFacturas {
  docenteId?: string
  estado?: EstadoFactura
  desde?: string
  hasta?: string
}

export interface KpisLiquidacion {
  totalSinFactura: number
  totalConFactura: number
  totalNexo: number
}
