import { useState } from 'react'
import { useAsignacionesTenant } from '../hooks/useEquipos'
import { exportarEquipoCsvUrl } from '../services/equiposApi'
import type { FiltrosAsignaciones, RolEquipo } from '../types'

const ROLES: RolEquipo[] = ['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR']

export function AsignacionesAdminPage() {
  const [filtros, setFiltros] = useState<FiltrosAsignaciones>({})
  const [materiaInput, setMateriaInput] = useState('')
  const [rolInput, setRolInput] = useState<RolEquipo | ''>('')

  const { data: asignaciones = [], isLoading } = useAsignacionesTenant({
    ...filtros,
    docenteNombre: filtros.docenteNombre,
  })

  function applyFilters() {
    setFiltros({
      docenteNombre: materiaInput || undefined,
      rol: rolInput || undefined,
    })
  }

  function clearFilters() {
    setMateriaInput('')
    setRolInput('')
    setFiltros({})
  }

  const exportUrl = exportarEquipoCsvUrl(filtros)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Asignaciones del Equipo Docente</h1>
        <a
          href={exportUrl}
          className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 transition-colors"
          role="button"
          aria-label="Exportar"
        >
          Exportar CSV
        </a>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex gap-3 flex-wrap items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Docente / Materia</label>
          <input
            type="text"
            placeholder="Buscar materia o docente…"
            value={materiaInput}
            onChange={(e) => { setMateriaInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-56"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="rol-select" className="text-xs font-medium text-gray-500">
            Rol
          </label>
          <select
            id="rol-select"
            aria-label="Rol"
            value={rolInput}
            onChange={(e) => { setRolInput(e.target.value as RolEquipo | '') }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">Todos los roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={applyFilters}
          className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          Filtrar
        </button>
        <button
          type="button"
          onClick={clearFilters}
          className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded-md text-sm font-medium hover:bg-gray-50"
          aria-label="Limpiar filtros"
        >
          Limpiar
        </button>
      </div>

      {/* Table */}
      {isLoading && <p className="text-gray-500 text-sm">Cargando asignaciones…</p>}

      {!isLoading && asignaciones.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin asignaciones</p>
          <p className="text-sm mt-1">No hay asignaciones que coincidan con los filtros.</p>
        </div>
      )}

      {!isLoading && asignaciones.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Docente
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Carrera / Cohorte
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Rol
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {asignaciones.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">
                    {a.docenteNombre} {a.docenteApellido}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{a.materiaNombre}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {a.carreraNombre} / {a.cohorteNombre}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-medium">
                      {a.rol}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        a.estado === 'activa'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {a.estado}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
