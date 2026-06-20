import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useColoquiosMetricas, useConvocatorias, useCrearConvocatoria } from '../hooks/useCoordinacion'
import type { CrearConvocatoriaPayload } from '../types'

function KpiCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
      <p className="text-3xl font-bold text-indigo-600">{value}</p>
      <p className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">{label}</p>
    </div>
  )
}

function NuevaConvocatoriaModal({
  onClose,
}: {
  onClose: () => void
}) {
  const mutation = useCrearConvocatoria()
  const [form, setForm] = useState<CrearConvocatoriaPayload>({
    materiaId: '',
    instanciaNombre: '',
    diasDisponibles: [],
    cuposPorDia: 10,
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await mutation.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Nueva Convocatoria</h2>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label htmlFor="materiaId-conv" className="block text-sm font-medium text-gray-700 mb-1">
              Materia
            </label>
            <input
              id="materiaId-conv"
              value={form.materiaId}
              onChange={(e) => { setForm({ ...form, materiaId: e.target.value }) }}
              className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
              placeholder="ID de materia"
              required
            />
          </div>
          <div>
            <label htmlFor="instancia" className="block text-sm font-medium text-gray-700 mb-1">
              Nombre de instancia
            </label>
            <input
              id="instancia"
              value={form.instanciaNombre}
              onChange={(e) => { setForm({ ...form, instanciaNombre: e.target.value }) }}
              className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
              placeholder="Ej: Primer período 2024"
              required
            />
          </div>
          <div>
            <label htmlFor="cupos" className="block text-sm font-medium text-gray-700 mb-1">
              Cupos por día
            </label>
            <input
              id="cupos"
              type="number"
              min={1}
              value={form.cuposPorDia}
              onChange={(e) => { setForm({ ...form, cuposPorDia: Number(e.target.value) }) }}
              className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
            />
          </div>
          <div className="flex gap-3 justify-end mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-600 rounded-md text-sm"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium disabled:opacity-50"
            >
              {mutation.isPending ? 'Creando…' : 'Crear convocatoria'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ColoquiosPage() {
  const [showModal, setShowModal] = useState(false)
  const { data: metricas } = useColoquiosMetricas()
  const { data: convocatorias = [], isLoading } = useConvocatorias()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Coloquios</h1>
        <button
          type="button"
          onClick={() => { setShowModal(true) }}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
          aria-label="Nueva convocatoria"
        >
          + Nueva convocatoria
        </button>
      </div>

      {/* KPI panel */}
      {metricas && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <KpiCard label="Alumnos cargados" value={metricas.totalAlumnosCargados} />
          <KpiCard label="Instancias activas" value={metricas.instanciasActivas} />
          <KpiCard label="Reservas activas" value={metricas.reservasActivas} />
          <KpiCard label="Notas registradas" value={metricas.notasRegistradas} />
        </div>
      )}

      {/* Convocatorias list */}
      {isLoading && <p className="text-gray-500 text-sm">Cargando convocatorias…</p>}

      {!isLoading && convocatorias.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin convocatorias activas</p>
          <p className="text-sm mt-1">Creá la primera convocatoria con el botón de arriba.</p>
        </div>
      )}

      {!isLoading && convocatorias.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Materia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Instancia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Convocados
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Reservas
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Notas
                </th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {convocatorias.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{c.materiaNombre}</td>
                  <td className="px-4 py-3 text-gray-700">{c.instanciaNombre}</td>
                  <td className="px-4 py-3 text-gray-600">{c.totalAlumnosConvocados}</td>
                  <td className="px-4 py-3 text-gray-600">{c.reservasActivas}</td>
                  <td className="px-4 py-3 text-gray-600">{c.notasRegistradas}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/coordinacion/coloquios/${c.id}`}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      Ver detalle
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && <NuevaConvocatoriaModal onClose={() => { setShowModal(false) }} />}
    </div>
  )
}
