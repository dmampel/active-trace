import { useState } from 'react'
import { useCohortes, useCrearCohorte, useEditarCohorte, useCarreras } from '../hooks/useAdmin'

export function CohorteAdminPage() {
  const { data: cohortes = [], isLoading } = useCohortes()
  const { data: carreras = [] } = useCarreras()
  const crear = useCrearCohorte()
  const editar = useEditarCohorte()

  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({ nombre: '', anioInicio: '', desde: '', hasta: '', carreraId: '' })

  async function handleCrear(e: React.FormEvent) {
    e.preventDefault()
    try {
      await crear.mutateAsync({ ...form, anioInicio: Number(form.anioInicio) })
      setMostrarForm(false)
      setForm({ nombre: '', anioInicio: '', desde: '', hasta: '', carreraId: '' })
    } catch {
      // handled by mutation state
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Cohortes</h1>
        <button
          type="button"
          onClick={() => setMostrarForm(!mostrarForm)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          Nueva cohorte
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={(e) => void handleCrear(e)} className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 flex flex-wrap gap-4 items-end">
          {[
            { id: 'cohorte-nombre', label: 'Nombre', field: 'nombre' as const, type: 'text' },
            { id: 'cohorte-anio', label: 'Año de inicio', field: 'anioInicio' as const, type: 'number' },
            { id: 'cohorte-desde', label: 'Desde', field: 'desde' as const, type: 'date' },
            { id: 'cohorte-hasta', label: 'Hasta', field: 'hasta' as const, type: 'date' },
          ].map(({ id, label, field, type }) => (
            <div key={field}>
              <label htmlFor={id} className="block text-xs text-gray-600 mb-1">{label}</label>
              <input
                id={id}
                aria-label={label}
                type={type}
                value={form[field]}
                onChange={(e) => setForm((p) => ({ ...p, [field]: e.target.value }))}
                required
                className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-36"
              />
            </div>
          ))}
          <div>
            <label htmlFor="cohorte-carrera" className="block text-xs text-gray-600 mb-1">Carrera</label>
            <select
              id="cohorte-carrera"
              value={form.carreraId}
              onChange={(e) => setForm((p) => ({ ...p, carreraId: e.target.value }))}
              required
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm"
            >
              <option value="">Seleccioná…</option>
              {carreras.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </div>
          <button type="submit" disabled={crear.isPending} className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50">Guardar</button>
          <button type="button" onClick={() => setMostrarForm(false)} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50">Cancelar</button>
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Carrera</th>
              <th className="py-2 pr-4">Desde</th>
              <th className="py-2 pr-4">Hasta</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {cohortes.map((c) => (
              <tr key={c.id} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-medium">{c.nombre}</td>
                <td className="py-2 pr-4 text-gray-500">{c.carreraNombre}</td>
                <td className="py-2 pr-4">{c.desde}</td>
                <td className="py-2 pr-4">{c.hasta}</td>
                <td className="py-2 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {c.activa ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => void editar.mutateAsync({ id: c.id, payload: { activa: !c.activa } })}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    {c.activa ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
            {cohortes.length === 0 && (
              <tr><td colSpan={6} className="py-8 text-center text-gray-400 text-sm">Sin cohortes</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
