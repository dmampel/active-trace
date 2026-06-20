import { useParams } from 'react-router-dom'
import { useMonitorDocente } from '../hooks/useMonitorDocente'
import type { AlumnoMonitor } from '../types'

export function MonitorDocentePage() {
  const { comisionId = '' } = useParams()
  const { alumnos, isLoading, filtros, setFiltros, clearFiltros } = useMonitorDocente(comisionId)

  const hayFiltros = Object.values(filtros).some((v) => v !== undefined && v !== '')

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Monitor de seguimiento</h1>
        {hayFiltros && (
          <button
            type="button"
            onClick={clearFiltros}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Alumno (nombre o correo)</label>
          <input
            type="text"
            value={filtros.alumno ?? ''}
            onChange={(e) => setFiltros({ ...filtros, alumno: e.target.value || undefined })}
            placeholder="Buscar alumno…"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-full"
            aria-label="Filtrar por alumno"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Comisión</label>
          <input
            type="text"
            value={filtros.comision ?? ''}
            onChange={(e) => setFiltros({ ...filtros, comision: e.target.value || undefined })}
            placeholder="Nombre de comisión…"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-full"
            aria-label="Filtrar por comisión"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Regional</label>
          <input
            type="text"
            value={filtros.regional ?? ''}
            onChange={(e) => setFiltros({ ...filtros, regional: e.target.value || undefined })}
            placeholder="Regional…"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-full"
            aria-label="Filtrar por regional"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Actividad</label>
          <input
            type="text"
            value={filtros.actividad ?? ''}
            onChange={(e) => setFiltros({ ...filtros, actividad: e.target.value || undefined })}
            placeholder="Nombre de actividad…"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-full"
            aria-label="Filtrar por actividad"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Mínimo de actividades cumplidas</label>
          <input
            type="number"
            value={filtros.minimoActividades ?? ''}
            onChange={(e) =>
              setFiltros({
                ...filtros,
                minimoActividades: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            placeholder="0"
            min={0}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-full"
            aria-label="Filtrar por mínimo de actividades"
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : alumnos.length === 0 ? (
        <p className="text-sm text-gray-500">No hay alumnos que coincidan con los filtros.</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-600">
              <th className="py-2 pr-4">Alumno</th>
              <th className="py-2 pr-4">Comisión</th>
              <th className="py-2 pr-4">Regional</th>
              <th className="py-2 pr-4">Actividad</th>
              <th className="py-2">Cumplidas</th>
            </tr>
          </thead>
          <tbody>
            {alumnos.map((a: AlumnoMonitor) => (
              <tr key={a.id} className="border-b border-gray-100">
                <td className="py-2 pr-4">
                  {a.apellido}, {a.nombre}
                </td>
                <td className="py-2 pr-4">{a.comision}</td>
                <td className="py-2 pr-4">{a.regional}</td>
                <td className="py-2 pr-4">{a.actividad}</td>
                <td className="py-2">{a.actividadesCumplidas}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
