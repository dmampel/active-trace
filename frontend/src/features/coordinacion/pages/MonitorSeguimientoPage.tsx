import { useState } from 'react'
import { useMonitorSeguimiento } from '../hooks/useCoordinacion'
import type { FiltrosMonitor } from '../types'

export function MonitorSeguimientoPage() {
  const [filtros, setFiltros] = useState<FiltrosMonitor>({})
  const [materiaInput, setMateriaInput] = useState('')
  const [estadoInput, setEstadoInput] = useState('')
  const [fechaDesdeInput, setFechaDesdeInput] = useState('')
  const [fechaHastaInput, setFechaHastaInput] = useState('')

  const { data: alumnos = [], isLoading } = useMonitorSeguimiento(filtros)

  function handleBuscar() {
    setFiltros({
      materiaId: materiaInput || undefined,
      estado: estadoInput || undefined,
      fechaDesde: fechaDesdeInput || undefined,
      fechaHasta: fechaHastaInput || undefined,
    })
  }

  function clearFilters() {
    setMateriaInput('')
    setEstadoInput('')
    setFechaDesdeInput('')
    setFechaHastaInput('')
    setFiltros({})
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Monitor de Seguimiento</h1>

      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex gap-3 flex-wrap items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Materia</label>
          <input
            type="text"
            placeholder="Filtrar por materia…"
            value={materiaInput}
            onChange={(e) => { setMateriaInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-40"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fecha-desde" className="text-xs font-medium text-gray-500">
            Fecha desde
          </label>
          <input
            id="fecha-desde"
            type="date"
            value={fechaDesdeInput}
            onChange={(e) => { setFechaDesdeInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fecha-hasta" className="text-xs font-medium text-gray-500">
            Fecha hasta
          </label>
          <input
            id="fecha-hasta"
            type="date"
            value={fechaHastaInput}
            onChange={(e) => { setFechaHastaInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={handleBuscar}
          className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium"
          aria-label="Buscar"
        >
          Buscar
        </button>
        <button
          type="button"
          onClick={clearFilters}
          className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded-md text-sm font-medium"
          aria-label="Limpiar filtros"
        >
          Limpiar
        </button>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Cargando monitor…</p>}

      {!isLoading && alumnos.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin resultados</p>
          <p className="text-sm mt-1">
            Seleccioná un rango de fechas y aplicá los filtros para ver los alumnos.
          </p>
        </div>
      )}

      {!isLoading && alumnos.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Alumno
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Actividades
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alumnos.map((a) => (
                <tr key={a.alumnoId} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">
                    {a.alumnoNombre} {a.alumnoApellido}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{a.materia}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        a.estado === 'Al día'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {a.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.actividadesCumplidas}/{a.actividadesTotales}
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
