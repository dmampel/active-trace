import { useState } from 'react'
import { useMaterias, useCrearMateria, useEditarMateria } from '../hooks/useAdmin'

export function MateriasPage() {
  const { data: materias = [], isLoading } = useMaterias()
  const crear = useCrearMateria()
  const editar = useEditarMateria()

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

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Materias</h1>
        <button
          type="button"
          onClick={() => setMostrarForm(!mostrarForm)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          Nueva materia
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={(e) => void handleCrear(e)} className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 flex items-end gap-4">
          <div>
            <label htmlFor="materia-codigo" className="block text-xs text-gray-600 mb-1">Código</label>
            <input
              id="materia-codigo"
              aria-label="Código"
              value={form.codigo}
              onChange={(e) => setForm((p) => ({ ...p, codigo: e.target.value }))}
              required
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-28"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="materia-nombre" className="block text-xs text-gray-600 mb-1">Nombre</label>
            <input
              id="materia-nombre"
              aria-label="Nombre"
              value={form.nombre}
              onChange={(e) => setForm((p) => ({ ...p, nombre: e.target.value }))}
              required
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-full"
            />
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
              <th className="py-2 pr-4">Código</th>
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {materias.map((m) => (
              <tr key={m.id} className="border-b border-gray-100">
                <td className="py-2 pr-4 font-mono text-xs">{m.codigo}</td>
                <td className="py-2 pr-4">{m.nombre}</td>
                <td className="py-2 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${m.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {m.activa ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => void editar.mutateAsync({ id: m.id, payload: { activa: !m.activa } })}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    {m.activa ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
            {materias.length === 0 && (
              <tr><td colSpan={4} className="py-8 text-center text-gray-400 text-sm">Sin materias</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
