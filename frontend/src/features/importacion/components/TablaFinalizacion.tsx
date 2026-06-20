import type { FinalizacionItem } from '../types'

interface TablaFinalizacionProps {
  items: FinalizacionItem[]
  onExportCsv: () => void
}

export function TablaFinalizacion({ items, onExportCsv }: TablaFinalizacionProps) {
  const isEmpty = items.length === 0

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800">Posibles entregas sin corregir</h3>
        <button
          type="button"
          onClick={onExportCsv}
          disabled={isEmpty}
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Exportar CSV
        </button>
      </div>
      {isEmpty ? (
        <p className="text-sm text-gray-500">No se detectaron entregas sin corregir</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-600">
              <th className="py-2 pr-4">Alumno</th>
              <th className="py-2 pr-4">Actividad</th>
              <th className="py-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-gray-100">
                <td className="py-2 pr-4">
                  {item.alumnoNombre} ({item.alumnoEmail})
                </td>
                <td className="py-2 pr-4">{item.actividad}</td>
                <td className="py-2">{item.estado}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export function exportFinalizacionCsv(items: FinalizacionItem[]): void {
  const header = 'alumno,email,actividad,estado'
  const rows = items.map(
    (i) => `"${i.alumnoNombre}","${i.alumnoEmail}","${i.actividad}","${i.estado}"`,
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'finalizacion.csv'
  a.click()
  URL.revokeObjectURL(url)
}
