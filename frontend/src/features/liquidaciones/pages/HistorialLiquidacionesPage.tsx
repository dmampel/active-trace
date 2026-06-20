import { useHistorialLiquidaciones } from '../hooks/useLiquidaciones'

export function HistorialLiquidacionesPage() {
  const { data: historial = [], isLoading } = useHistorialLiquidaciones()

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Historial de Liquidaciones</h1>

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : historial.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin historial de liquidaciones</p>
          <p className="text-sm mt-1">Aún no se cerraron períodos.</p>
        </div>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
              <th className="py-2 pr-4">Período</th>
              <th className="py-2 pr-4">Docente</th>
              <th className="py-2 pr-4">Rol</th>
              <th className="py-2 pr-4 text-right">Base</th>
              <th className="py-2 pr-4 text-right">Plus</th>
              <th className="py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {historial.map((l) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-mono text-xs">{l.periodo}</td>
                <td className="py-2 pr-4">{l.docente.apellido}, {l.docente.nombre}</td>
                <td className="py-2 pr-4 text-gray-500">{l.docente.rol}</td>
                <td className="py-2 pr-4 text-right">${l.salarioBase.toLocaleString('es-AR')}</td>
                <td className="py-2 pr-4 text-right">${l.plus.toLocaleString('es-AR')}</td>
                <td className="py-2 text-right font-semibold">${l.total.toLocaleString('es-AR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
