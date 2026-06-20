import { useSearchParams } from 'react-router-dom'
import { useFacturas, useMarcarFacturaAbonada } from '../hooks/useLiquidaciones'
import type { EstadoFactura } from '../types'

export function FacturasPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const estadoFiltro = (searchParams.get('estado') ?? '') as EstadoFactura | ''

  const { data: facturas = [], isLoading } = useFacturas(
    estadoFiltro ? { estado: estadoFiltro } : {},
  )
  const marcar = useMarcarFacturaAbonada()

  function setEstado(v: string) {
    if (v) setSearchParams({ estado: v })
    else setSearchParams({})
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Facturas</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="filtro-estado" className="text-sm text-gray-600">Estado:</label>
          <select
            id="filtro-estado"
            aria-label="Estado"
            value={estadoFiltro}
            onChange={(e) => setEstado(e.target.value)}
            className="border border-gray-300 rounded-md px-2 py-1.5 text-sm"
          >
            <option value="">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="abonada">Abonada</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
              <th className="py-2 pr-4">Docente</th>
              <th className="py-2 pr-4">Período</th>
              <th className="py-2 pr-4">Detalle</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2 pr-4">Cargada</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {facturas.map((f) => (
              <tr key={f.id} className="border-b border-gray-100">
                <td className="py-2 pr-4">{f.docenteApellido}, {f.docenteNombre}</td>
                <td className="py-2 pr-4">{f.periodo}</td>
                <td className="py-2 pr-4 text-gray-600">{f.detalle}</td>
                <td className="py-2 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    f.estado === 'abonada'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {f.estado}
                  </span>
                </td>
                <td className="py-2 pr-4 text-gray-400">{new Date(f.cargadaEn).toLocaleDateString('es-AR')}</td>
                <td className="py-2">
                  {f.estado === 'pendiente' && (
                    <button
                      type="button"
                      onClick={() => void marcar.mutate(f.id)}
                      disabled={marcar.isPending}
                      className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                    >
                      Marcar abonada
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {facturas.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">Sin facturas</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
