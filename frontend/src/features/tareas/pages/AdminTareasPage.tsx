import { useState } from 'react'
import { useAdminTareas, useCambiarEstadoTarea, useAgregarComentario } from '../hooks/useTareas'
import type { FiltrosTareas, EstadoTarea, Tarea } from '../types'

const ESTADOS: { value: EstadoTarea | ''; label: string }[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'abierta', label: 'Abierta' },
  { value: 'en_progreso', label: 'En progreso' },
  { value: 'completada', label: 'Completada' },
  { value: 'rechazada', label: 'Rechazada' },
]

function AdminTareaRow({ tarea }: { tarea: Tarea }) {
  const cambiarEstado = useCambiarEstadoTarea()
  const [showComentario, setShowComentario] = useState(false)
  const [comentarioTexto, setComentarioTexto] = useState('')
  const agregarComentario = useAgregarComentario(tarea.id)

  async function handleEnviarComentario() {
    if (!comentarioTexto.trim()) return
    await agregarComentario.mutateAsync({ texto: comentarioTexto })
    setComentarioTexto('')
    setShowComentario(false)
  }

  return (
    <>
      <tr className="hover:bg-gray-50">
        <td className="px-4 py-3 text-gray-900 font-medium">{tarea.titulo}</td>
        <td className="px-4 py-3 text-gray-500">{tarea.materiaNombre}</td>
        <td className="px-4 py-3 text-gray-700">
          {tarea.asignadoANombre} {tarea.asignadoAApellido}
        </td>
        <td className="px-4 py-3 text-gray-500">
          {tarea.asignadoPorNombre} {tarea.asignadoPorApellido}
        </td>
        <td className="px-4 py-3">
          <select
            value={tarea.estado}
            onChange={(e) => {
              void cambiarEstado.mutate({
                tareaId: tarea.id,
                payload: { estado: e.target.value as EstadoTarea },
              })
            }}
            className="border border-gray-300 rounded-md px-2 py-1 text-xs"
          >
            {ESTADOS.filter((e) => e.value !== '').map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </td>
        <td className="px-4 py-3 text-xs text-gray-400">
          {new Date(tarea.actualizadaEn).toLocaleDateString('es-AR')}
        </td>
        <td className="px-4 py-3">
          <button
            type="button"
            onClick={() => { setShowComentario(!showComentario) }}
            className="text-xs text-indigo-600 hover:underline"
          >
            Comentario
          </button>
        </td>
      </tr>
      {showComentario && (
        <tr>
          <td colSpan={7} className="px-4 py-2 bg-indigo-50">
            <div className="flex gap-2">
              <input
                type="text"
                value={comentarioTexto}
                onChange={(e) => { setComentarioTexto(e.target.value) }}
                placeholder="Observación del coordinador…"
                className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={handleEnviarComentario}
                disabled={agregarComentario.isPending}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium"
              >
                Enviar
              </button>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export function AdminTareasPage() {
  const [filtros, setFiltros] = useState<FiltrosTareas>({})
  const [estadoInput, setEstadoInput] = useState<EstadoTarea | ''>('')
  const [docenteInput, setDocenteInput] = useState('')

  const { data: tareas = [], isLoading } = useAdminTareas(filtros)

  function applyFilters() {
    setFiltros({
      estado: estadoInput || undefined,
      docenteId: docenteInput || undefined,
    })
  }

  function clearFilters() {
    setEstadoInput('')
    setDocenteInput('')
    setFiltros({})
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Administración de Tareas</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex gap-3 flex-wrap items-end">
        <div className="flex flex-col gap-1">
          <label htmlFor="estado-filter" className="text-xs font-medium text-gray-500">
            Estado
          </label>
          <select
            id="estado-filter"
            aria-label="Estado"
            value={estadoInput}
            onChange={(e) => { setEstadoInput(e.target.value as EstadoTarea | '') }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          >
            {ESTADOS.map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Docente</label>
          <input
            type="text"
            placeholder="Buscar docente…"
            value={docenteInput}
            onChange={(e) => { setDocenteInput(e.target.value) }}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-48"
          />
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
          aria-label="Limpiar filtros"
        >
          Limpiar
        </button>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Cargando tareas…</p>}

      {!isLoading && tareas.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin tareas</p>
        </div>
      )}

      {!isLoading && tareas.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Tarea
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Asignado a
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Asignado por
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Actualizado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tareas.map((t) => (
                <AdminTareaRow key={t.id} tarea={t} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
