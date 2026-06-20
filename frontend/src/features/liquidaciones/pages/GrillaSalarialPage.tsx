import { useState } from 'react'
import {
  useSalariosBase,
  useSalariosPlus,
  useCrearSalarioBase,
  useEliminarSalarioBase,
  useCrearSalarioPlus,
  useEliminarSalarioPlus,
} from '../hooks/useLiquidaciones'

const ROLES = ['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR']

function FormSalarioBase({ onCancel }: { onCancel: () => void }) {
  const [rol, setRol] = useState('')
  const [monto, setMonto] = useState('')
  const [desde, setDesde] = useState('')
  const crear = useCrearSalarioBase()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await crear.mutateAsync({ rol, monto: Number(monto), desde, hasta: null })
      onCancel()
    } catch {
      // handled by mutation state
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex items-end gap-3 mt-3 flex-wrap">
      <div>
        <label htmlFor="base-rol" className="block text-xs text-gray-600 mb-1">Rol</label>
        <select id="base-rol" aria-label="Rol" value={rol} onChange={(e) => setRol(e.target.value)} required className="border border-gray-300 rounded-md px-2 py-1.5 text-sm">
          <option value="">Seleccioná…</option>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="base-monto" className="block text-xs text-gray-600 mb-1">Monto</label>
        <input id="base-monto" aria-label="Monto" type="number" value={monto} onChange={(e) => setMonto(e.target.value)} required min={0} className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-32" />
      </div>
      <div>
        <label htmlFor="base-desde" className="block text-xs text-gray-600 mb-1">Desde</label>
        <input id="base-desde" aria-label="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required className="border border-gray-300 rounded-md px-2 py-1.5 text-sm" />
      </div>
      <button type="submit" disabled={crear.isPending} className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50">
        Guardar
      </button>
      <button type="button" onClick={onCancel} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50">
        Cancelar
      </button>
    </form>
  )
}

export function GrillaSalarialPage() {
  const { data: base = [], isLoading: loadingBase } = useSalariosBase()
  const { data: plus = [], isLoading: loadingPlus } = useSalariosPlus()
  const eliminarBase = useEliminarSalarioBase()
  const eliminarPlus = useEliminarSalarioPlus()
  const crearPlus = useCrearSalarioPlus()

  const [mostrarFormBase, setMostrarFormBase] = useState(false)
  const [mostrarFormPlus, setMostrarFormPlus] = useState(false)
  const [plusForm, setPlusForm] = useState({ clave: '', rol: '', descripcion: '', monto: '', desde: '' })

  async function handleCrearPlus(e: React.FormEvent) {
    e.preventDefault()
    try {
      await crearPlus.mutateAsync({ ...plusForm, monto: Number(plusForm.monto), hasta: null })
      setMostrarFormPlus(false)
      setPlusForm({ clave: '', rol: '', descripcion: '', monto: '', desde: '' })
    } catch {
      // handled by mutation state
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Grilla Salarial</h1>

      {/* Salarios base */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-700">Salarios Base</h2>
          <button type="button" onClick={() => setMostrarFormBase(!mostrarFormBase)} className="text-sm text-indigo-600 hover:underline">
            Agregar salario base
          </button>
        </div>

        {mostrarFormBase && <FormSalarioBase onCancel={() => setMostrarFormBase(false)} />}

        {loadingBase ? <p className="text-sm text-gray-500 mt-2">Cargando…</p> : (
          <table className="w-full text-sm border-collapse mt-3">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                <th className="py-1 pr-4">Rol</th>
                <th className="py-1 pr-4">Monto</th>
                <th className="py-1 pr-4">Desde</th>
                <th className="py-1 pr-4">Hasta</th>
                <th className="py-1">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {base.map((b) => (
                <tr key={b.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-medium">{b.rol}</td>
                  <td className="py-2 pr-4">${b.monto.toLocaleString('es-AR')}</td>
                  <td className="py-2 pr-4">{b.desde}</td>
                  <td className="py-2 pr-4 text-gray-400">{b.hasta ?? '—'}</td>
                  <td className="py-2">
                    <button type="button" onClick={() => void eliminarBase.mutate(b.id)} className="text-xs text-red-600 hover:underline">
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {base.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-gray-400 text-sm">Sin salarios base configurados</td></tr>}
            </tbody>
          </table>
        )}
      </section>

      {/* Salarios plus */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-700">Plus</h2>
          <button type="button" onClick={() => setMostrarFormPlus(!mostrarFormPlus)} className="text-sm text-indigo-600 hover:underline">
            Agregar plus
          </button>
        </div>

        {mostrarFormPlus && (
          <form onSubmit={(e) => void handleCrearPlus(e)} className="flex items-end gap-3 mt-3 flex-wrap">
            {(['clave', 'rol', 'descripcion', 'monto', 'desde'] as const).map((field) => (
              <div key={field}>
                <label htmlFor={`plus-${field}`} className="block text-xs text-gray-600 mb-1 capitalize">{field}</label>
                <input
                  id={`plus-${field}`}
                  type={field === 'monto' ? 'number' : field === 'desde' ? 'date' : 'text'}
                  value={plusForm[field]}
                  onChange={(e) => setPlusForm((p) => ({ ...p, [field]: e.target.value }))}
                  required
                  className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-36"
                />
              </div>
            ))}
            <button type="submit" disabled={crearPlus.isPending} className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50">Guardar</button>
            <button type="button" onClick={() => setMostrarFormPlus(false)} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50">Cancelar</button>
          </form>
        )}

        {loadingPlus ? <p className="text-sm text-gray-500 mt-2">Cargando…</p> : (
          <table className="w-full text-sm border-collapse mt-3">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                <th className="py-1 pr-4">Clave</th>
                <th className="py-1 pr-4">Rol</th>
                <th className="py-1 pr-4">Descripción</th>
                <th className="py-1 pr-4">Monto</th>
                <th className="py-1 pr-4">Desde</th>
                <th className="py-1">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {plus.map((p) => (
                <tr key={p.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-mono text-xs">{p.clave}</td>
                  <td className="py-2 pr-4">{p.rol}</td>
                  <td className="py-2 pr-4 text-gray-600">{p.descripcion}</td>
                  <td className="py-2 pr-4">${p.monto.toLocaleString('es-AR')}</td>
                  <td className="py-2 pr-4">{p.desde}</td>
                  <td className="py-2">
                    <button type="button" onClick={() => void eliminarPlus.mutate(p.id)} className="text-xs text-red-600 hover:underline">
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {plus.length === 0 && <tr><td colSpan={6} className="py-4 text-center text-gray-400 text-sm">Sin plus configurados</td></tr>}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
