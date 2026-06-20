import { useState } from 'react'
import { useEncuentrosAdmin, useGuardias } from '../hooks/useCoordinacion'
import { exportarGuardiasCsvUrl } from '../services/coordinacionApi'
import type { FiltrosEncuentros } from '../types'

export function EncuentrosAdminPage() {
  const [filtros, setFiltros] = useState<FiltrosEncuentros>({})
  const [materiaInput, setMateriaInput] = useState('')
  const [docenteInput, setDocenteInput] = useState('')
  const [estadoInput, setEstadoInput] = useState('')

  const { data: encuentros = [], isLoading: loadingEncuentros } = useEncuentrosAdmin(filtros)
  const { data: guardias = [], isLoading: loadingGuardias } = useGuardias({})
  const exportGuardiasUrl = exportarGuardiasCsvUrl({})

  function applyFilters() {
    setFiltros({
      materiaId: materiaInput || undefined,
      estado: estadoInput ? (estadoInput as 'programado' | 'en_curso' | 'realizado' | 'cancelado') : undefined,
    })
  }

  function clearFilters() {
    setMateriaInput('')
    setDocenteInput('')
    setEstadoInput('')
    setFiltros({})
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Encuentros (Admin)</h1>

      {/* Filters */}
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
          <label className="text-xs font-medium text-gray-500">Docente</label>
          <input
            type="text"
            placeholder="Filtrar por docente…"
            value={docenteInput}
            onChange={(e) => { setDocenteInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-40"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="estado-enc" className="text-xs font-medium text-gray-500">Estado</label>
          <select
            id="estado-enc"
            value={estadoInput}
            onChange={(e) => { setEstadoInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">Todos</option>
            <option value="programado">Programado</option>
            <option value="en_curso">En curso</option>
            <option value="realizado">Realizado</option>
            <option value="cancelado">Cancelado</option>
          </select>
        </div>
        <button
          type="button"
          onClick={applyFilters}
          className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm font-medium"
        >
          Filtrar
        </button>
        <button
          type="button"
          onClick={clearFilters}
          className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded-md text-sm font-medium"
        >
          Limpiar
        </button>
      </div>

      {/* Encuentros table */}
      {loadingEncuentros && <p className="text-gray-500 text-sm">Cargando encuentros…</p>}
      {!loadingEncuentros && encuentros.length === 0 && (
        <div className="text-center py-8 text-gray-400">
          <p>Sin encuentros que coincidan con los filtros.</p>
        </div>
      )}
      {!loadingEncuentros && encuentros.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-8">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Docente
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Fecha
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Grabación
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {encuentros.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{e.materiaNombre}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {e.docenteNombre} {e.docenteApellido}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{e.fecha}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      {e.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {e.grabacionUrl ? (
                      <a href={e.grabacionUrl} className="text-xs text-indigo-600 hover:underline">
                        Ver grabación
                      </a>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Guardias section */}
      <div className="mb-4 flex items-center justify-between">
        <h2 role="heading" className="text-lg font-semibold text-gray-800">Guardias</h2>
        <a
          href={exportGuardiasUrl}
          role="button"
          aria-label="Exportar guardias"
          onClick={(e) => { e.preventDefault() }}
          className="px-3 py-1.5 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700"
        >
          Exportar guardias
        </a>
      </div>

      {loadingGuardias && <p className="text-gray-500 text-sm">Cargando guardias…</p>}
      {!loadingGuardias && guardias.length === 0 && (
        <div className="text-center py-8 text-gray-400">
          <p>Sin guardias registradas.</p>
        </div>
      )}
      {!loadingGuardias && guardias.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Tutor
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Día
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Horario
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {guardias.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">
                    {g.tutorNombre} {g.tutorApellido}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{g.materiaNombre}</td>
                  <td className="px-4 py-3 text-gray-500">{g.dia}</td>
                  <td className="px-4 py-3 text-gray-500">{g.horario}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      {g.estado}
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
