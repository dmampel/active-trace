import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLiquidaciones, useCerrarLiquidacion } from '../hooks/useLiquidaciones'
import type { Liquidacion } from '../types'

function formatMoney(n: number) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(n)
}

function FilaDocente({ liq }: { liq: Liquidacion }) {
  return (
    <tr className="border-b border-gray-100 text-sm">
      <td className="py-2 pr-4">{liq.docente.apellido}, {liq.docente.nombre}</td>
      <td className="py-2 pr-4 text-gray-500">{liq.docente.rol}</td>
      <td className="py-2 pr-4 text-right">{formatMoney(liq.salarioBase)}</td>
      <td className="py-2 pr-4 text-right">{formatMoney(liq.plus)}</td>
      <td className="py-2 text-right font-semibold">{formatMoney(liq.total)}</td>
    </tr>
  )
}

function TablaSegmento({ titulo, filas }: { titulo: string; filas: Liquidacion[] }) {
  if (filas.length === 0) return null
  const subtotal = filas.reduce((acc, l) => acc + l.total, 0)
  return (
    <section className="mb-6">
      <h2 className="text-base font-semibold text-gray-700 mb-2">{titulo}</h2>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
            <th className="py-1 pr-4">Docente</th>
            <th className="py-1 pr-4">Rol</th>
            <th className="py-1 pr-4 text-right">Base</th>
            <th className="py-1 pr-4 text-right">Plus</th>
            <th className="py-1 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((l) => <FilaDocente key={l.id} liq={l} />)}
        </tbody>
        <tfoot>
          <tr className="border-t border-gray-300 text-sm font-semibold">
            <td colSpan={4} className="py-2 pr-4 text-right text-gray-600">Subtotal</td>
            <td className="py-2 text-right">{formatMoney(subtotal)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  )
}

export function LiquidacionesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const periodoParam = searchParams.get('periodo') ?? new Date().toISOString().slice(0, 7)
  const [periodo, setPeriodo] = useState(periodoParam)
  const [confirmando, setConfirmando] = useState(false)

  const { data: liquidaciones = [], isLoading } = useLiquidaciones(periodo)
  const cerrar = useCerrarLiquidacion()

  const general = liquidaciones.filter((l) => !l.esNexo && !l.excluidoPorFactura)
  const nexo = liquidaciones.filter((l) => l.esNexo)
  const factura = liquidaciones.filter((l) => l.excluidoPorFactura)

  const totalSinFactura = [...general, ...nexo].reduce((acc, l) => acc + l.total, 0)
  const totalConFactura = totalSinFactura + factura.reduce((acc, l) => acc + l.total, 0)

  const yaCerrada = liquidaciones.length > 0 && liquidaciones.every((l) => l.estado === 'cerrada')

  function handleCambiarPeriodo(p: string) {
    setPeriodo(p)
    setSearchParams({ periodo: p })
  }

  async function handleCerrar() {
    try {
      await cerrar.mutateAsync(periodo)
      setConfirmando(false)
    } catch (error) {
      console.error('MUTATION ERROR:', error)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Liquidaciones</h1>
        <div className="flex items-center gap-3">
          <label htmlFor="periodo-select" className="text-sm text-gray-600">Período:</label>
          <input
            id="periodo-select"
            type="month"
            value={periodo}
            onChange={(e) => handleCambiarPeriodo(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
          <p className="text-xs text-indigo-600 uppercase font-semibold mb-1">Total sin factura</p>
          <p className="text-2xl font-bold text-indigo-800">{formatMoney(totalSinFactura)}</p>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Total con factura</p>
          <p className="text-2xl font-bold text-gray-800">{formatMoney(totalConFactura)}</p>
        </div>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      {!isLoading && (
        <>
          <TablaSegmento titulo="General (PROFESOR / TUTOR / COORDINADOR sin factura)" filas={general} />
          <TablaSegmento titulo="NEXO" filas={nexo} />
          <TablaSegmento titulo="Docentes que facturan (informativo — excluidos del total)" filas={factura} />

          {liquidaciones.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p>Sin liquidaciones para el período {periodo}</p>
            </div>
          )}

          {/* Cerrar liquidación */}
          <div className="mt-6 flex items-center gap-3">
            {!confirmando ? (
              <button
                type="button"
                disabled={yaCerrada || liquidaciones.length === 0}
                onClick={() => setConfirmando(true)}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Cerrar período
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">¿Confirmar cierre? Esta acción es irreversible.</span>
                <button
                  type="button"
                  onClick={() => void handleCerrar()}
                  disabled={cerrar.isPending}
                  className="px-3 py-1.5 bg-red-600 text-white rounded-md text-xs font-medium hover:bg-red-700 disabled:opacity-50"
                >
                  Confirmar
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmando(false)}
                  className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50"
                >
                  Cancelar
                </button>
              </div>
            )}
            {yaCerrada && <span className="text-sm text-gray-400">Período cerrado (inmutable)</span>}
          </div>
        </>
      )}
    </div>
  )
}
