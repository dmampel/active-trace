import { useState } from 'react'
import { useCarreras, useCrearCarrera, useEditarCarrera } from '../hooks/useAdmin'

export function CarrerasPage() {
  const { data: carreras = [], isLoading } = useCarreras()
  const crear = useCrearCarrera()
  const editar = useEditarCarrera()

  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({ codigo: '', nombre: '' })

  async function handleCrear(e: React.FormEvent) {
    e.preventDefault()
    try {
      await crear.mutateAsync(form)
      setMostrarForm(false)
      setForm({ codigo: '', nombre: '' })
    } catch {
      // handled by mutation state
    }
  }

  async function handleToggleActiva(id: string, activa: boolean) {
    await editar.mutateAsync({ id, payload: { activa: !activa } })
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Carreras</h1>
        <button
          type="button"
          onClick={() => setMostrarForm(!mostrarForm)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          Nueva carrera
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={(e) => void handleCrear(e)} className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 flex items-end gap-4">
          <div>
            <label htmlFor="carrera-codigo" className="block text-xs text-gray-600 mb-1">Código</label>
            <input
              id="carrera-codigo"
              aria-label="Código"
              value={form.codigo}
              onChange={(e) => setForm((p) => ({ ...p, codigo: e.target.value }))}
              required
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-28"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="carrera-nombre" className="block text-xs text-gray-600 mb-1">Nombre</label>
            <input
              id="carrera-nombre"
              aria-label="Nombre"
              value={form.nombre}
              onChange={(e) => setForm((p) => ({ ...p, nombre: e.target.value }))}
              required
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-full"
            />
          </div>
          <button type="submit" disabled={crear.isPending} className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50">
            Guardar
          </button>
          <button type="button" onClick={() => setMostrarForm(false)} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50">
            Cancelar
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
              <th className="py-2 pr-4">Código</th>
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {carreras.map((c) => (
              <tr key={c.id} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-mono text-xs">{c.codigo}</td>
                <td className="py-2 pr-4">{c.nombre}</td>
                <td className="py-2 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {c.activa ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => void handleToggleActiva(c.id, c.activa)}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    {c.activa ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
            {carreras.length === 0 && (
              <tr><td colSpan={4} className="py-8 text-center text-gray-400 text-sm">Sin carreras</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
