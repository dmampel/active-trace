import { useState, useMemo } from 'react'
import type { AlumnoAtrasado } from '../types'

type SortKey = keyof Pick<AlumnoAtrasado, 'nombre' | 'apellido' | 'email' | 'actividadesFaltantes' | 'nota'>
type SortDir = 'asc' | 'desc'

interface TablaAtrasadosProps {
  alumnos: AlumnoAtrasado[]
}

export function TablaAtrasados({ alumnos }: TablaAtrasadosProps) {
  const [busqueda, setBusqueda] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('apellido')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const filtered = useMemo(() => {
    const q = busqueda.toLowerCase()
    return alumnos.filter(
      (a) =>
        a.nombre.toLowerCase().includes(q) ||
        a.apellido.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q),
    )
  }, [alumnos, busqueda])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [filtered, sortKey, sortDir])

  return (
    <div>
      <div className="mb-3">
        <input
          type="text"
          placeholder="Buscar por nombre o correo…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-72"
          aria-label="Buscar alumno"
        />
      </div>
      {sorted.length === 0 ? (
        <p className="text-sm text-gray-500" data-testid="empty-atrasados">
          {busqueda ? 'Sin resultados para tu búsqueda.' : '¡Todos los alumnos están al día!'}
        </p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-600">
              {(
                [
                  { key: 'apellido' as SortKey, label: 'Nombre' },
                  { key: 'email' as SortKey, label: 'Correo' },
                  { key: 'actividadesFaltantes' as SortKey, label: 'Actividades faltantes' },
                  { key: 'nota' as SortKey, label: 'Nota' },
                ] as { key: SortKey; label: string }[]
              ).map(({ key, label }) => (
                <th
                  key={key}
                  className="py-2 pr-4 cursor-pointer hover:text-gray-900 select-none"
                  onClick={() => handleSort(key)}
                >
                  {label}
                  {sortKey === key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((a) => (
              <tr key={a.id} className="border-b border-gray-100">
                <td className="py-2 pr-4">
                  {a.apellido}, {a.nombre}
                </td>
                <td className="py-2 pr-4">{a.email}</td>
                <td className="py-2 pr-4">{a.actividadesFaltantes}</td>
                <td className="py-2">{a.nota}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
