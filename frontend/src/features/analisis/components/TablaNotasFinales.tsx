import type { NotaFinal } from '../types'

interface TablaNotasFinalesProps {
  notas: NotaFinal[]
}

export function exportNotasFinalesCsv(notas: NotaFinal[]): void {
  const header = 'apellido,nombre,email,nota_final'
  const rows = notas.map(
    (n) => `"${n.apellido}","${n.nombre}","${n.email}","${n.notaFinal}"`,
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'notas-finales.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export function TablaNotasFinales({ notas }: TablaNotasFinalesProps) {
  const handleExport = () => exportNotasFinalesCsv(notas)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800">Notas finales</h3>
        <button
          type="button"
          onClick={handleExport}
          disabled={notas.length === 0}
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50"
        >
          Exportar CSV
        </button>
      </div>
      {notas.length === 0 ? (
        <p className="text-sm text-gray-500">No hay notas finales disponibles.</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-600">
              <th className="py-2 pr-4">Alumno</th>
              <th className="py-2 pr-4">Correo</th>
              <th className="py-2">Nota final</th>
            </tr>
          </thead>
          <tbody>
            {notas.map((n) => (
              <tr key={n.id} className="border-b border-gray-100">
                <td className="py-2 pr-4">
                  {n.apellido}, {n.nombre}
                </td>
                <td className="py-2 pr-4">{n.email}</td>
                <td className="py-2">{n.notaFinal}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
