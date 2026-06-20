import { useState, useMemo } from 'react'
import type { AlumnoRanking } from '../types'

type SortKey = keyof Pick<AlumnoRanking, 'nombre' | 'apellido' | 'actividadesAprobadas' | 'nota'>
type SortDir = 'asc' | 'desc'

interface TablaRankingProps {
  alumnos: AlumnoRanking[]
}

export function TablaRanking({ alumnos }: TablaRankingProps) {
  const [sortKey, setSortKey] = useState<SortKey>('actividadesAprobadas')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const filtered = useMemo(
    () => alumnos.filter((a) => a.actividadesAprobadas > 0),
    [alumnos],
  )

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [filtered, sortKey, sortDir])

  if (sorted.length === 0) {
    return <p className="text-sm text-gray-500">No hay alumnos con actividades aprobadas.</p>
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b border-gray-200 text-left text-gray-600">
          {(
            [
              { key: 'apellido' as SortKey, label: 'Alumno' },
              { key: 'actividadesAprobadas' as SortKey, label: 'Aprobadas' },
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
            <td className="py-2 pr-4">{a.actividadesAprobadas}</td>
            <td className="py-2">{a.nota}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
