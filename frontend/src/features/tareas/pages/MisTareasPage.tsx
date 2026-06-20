import { useState } from 'react'
import { useMisTareas, useAgregarComentario, useCambiarEstadoTarea } from '../hooks/useTareas'
import type { Tarea, EstadoTarea } from '../types'

const ESTADOS: { value: EstadoTarea; label: string }[] = [
  { value: 'abierta', label: 'Abierta' },
  { value: 'en_progreso', label: 'En progreso' },
  { value: 'completada', label: 'Completada' },
  { value: 'rechazada', label: 'Rechazada' },
]

function TareaCard({ tarea }: { tarea: Tarea }) {
  const [expandido, setExpandido] = useState(false)
  const [comentarioTexto, setComentarioTexto] = useState('')
  const agregarComentario = useAgregarComentario(tarea.id)
  const cambiarEstado = useCambiarEstadoTarea()

  async function handleEnviarComentario() {
    if (!comentarioTexto.trim()) return
    await agregarComentario.mutateAsync({ texto: comentarioTexto })
    setComentarioTexto('')
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-gray-800">{tarea.titulo}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{tarea.materiaNombre}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Asignada por {tarea.asignadoPorNombre} {tarea.asignadoPorApellido}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor={`estado-${tarea.id}`} className="sr-only">
            Estado de {tarea.titulo}
          </label>
          <select
            id={`estado-${tarea.id}`}
            aria-label="Estado"
            value={tarea.estado}
            onChange={(e) => {
              void cambiarEstado.mutate({
                tareaId: tarea.id,
                payload: { estado: e.target.value as EstadoTarea },
              })
            }}
            className="border border-gray-300 rounded-md px-2 py-1 text-xs"
          >
            {ESTADOS.map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {tarea.descripcion && (
        <p className="text-sm text-gray-600 mt-2">{tarea.descripcion}</p>
      )}

      {/* Toggle comment thread */}
      <button
        type="button"
        onClick={() => { setExpandido(!expandido) }}
        className="mt-3 text-xs text-indigo-600 hover:underline"
      >
        {tarea.comentarios.length > 0
          ? `${expandido ? 'Ocultar' : 'Ver'} ${tarea.comentarios.length} comentario${tarea.comentarios.length !== 1 ? 's' : ''}`
          : expandido
          ? 'Cerrar'
          : 'Agregar comentario'}
      </button>

      {expandido && (
        <div className="mt-3">
          {/* Thread */}
          {tarea.comentarios.map((c) => (
            <div key={c.id} className="mb-2 p-2 bg-gray-50 rounded-md text-sm">
              <span className="font-medium text-gray-700">
                {c.autorNombre} {c.autorApellido}:
              </span>{' '}
              <span className="text-gray-600">{c.texto}</span>
            </div>
          ))}

          {/* Add comment */}
          <div className="flex gap-2 mt-2">
            <input
              type="text"
              value={comentarioTexto}
              onChange={(e) => { setComentarioTexto(e.target.value) }}
              placeholder="Agregar comentario…"
              className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={handleEnviarComentario}
              disabled={agregarComentario.isPending}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
              aria-label="Enviar comentario"
            >
              Enviar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function MisTareasPage() {
  const { data: tareas = [], isLoading } = useMisTareas()

  // Sort by estado (abierta first) then by fecha
  const tareasOrdenadas = [...tareas].sort((a, b) => {
    const orden: Record<EstadoTarea, number> = {
      abierta: 0,
      en_progreso: 1,
      completada: 2,
      rechazada: 3,
    }
    const estadoDiff = (orden[a.estado] ?? 9) - (orden[b.estado] ?? 9)
    if (estadoDiff !== 0) return estadoDiff
    return new Date(a.creadaEn).getTime() - new Date(b.creadaEn).getTime()
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Mis Tareas</h1>

      {isLoading && <p className="text-gray-500 text-sm">Cargando tareas…</p>}

      {!isLoading && tareasOrdenadas.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin tareas asignadas</p>
          <p className="text-sm mt-1">No tenés tareas pendientes.</p>
        </div>
      )}

      {!isLoading && tareasOrdenadas.map((t) => <TareaCard key={t.id} tarea={t} />)}
    </div>
  )
}
