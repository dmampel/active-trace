import { useState } from 'react'
import { useUsuariosAdmin, useCrearUsuario, useEditarUsuario } from '../hooks/useAdmin'

const ROLES_OPCIONES = ['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR', 'FINANZAS', 'ADMIN']

export function UsuariosAdminPage() {
  const [filtroActivo, setFiltroActivo] = useState<boolean | undefined>(undefined)
  const { data: usuarios = [], isLoading } = useUsuariosAdmin(filtroActivo)
  const crear = useCrearUsuario()
  const editar = useEditarUsuario()
  const [editError, setEditError] = useState<string | null>(null)

  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({
    nombre: '', apellido: '', email: '', password: '', roles: [] as string[], modalidadCobro: 'liquidacion' as 'factura' | 'liquidacion',
  })

  async function handleCrear(e: React.FormEvent) {
    e.preventDefault()
    try {
      await crear.mutateAsync(form)
      setMostrarForm(false)
      setForm({ nombre: '', apellido: '', email: '', password: '', roles: [], modalidadCobro: 'liquidacion' })
    } catch {
      // handled by mutation state
    }
  }

  function toggleRol(rol: string) {
    setForm((p) => ({
      ...p,
      roles: p.roles.includes(rol) ? p.roles.filter((r) => r !== rol) : [...p.roles, rol],
    }))
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Usuarios</h1>
        <div className="flex items-center gap-3">
          <select
            value={filtroActivo === undefined ? '' : String(filtroActivo)}
            onChange={(e) => setFiltroActivo(e.target.value === '' ? undefined : e.target.value === 'true')}
            className="border border-gray-300 rounded-md px-2 py-1.5 text-sm"
            aria-label="Filtro activo"
          >
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
          <button
            type="button"
            onClick={() => setMostrarForm(!mostrarForm)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
          >
            Nuevo usuario
          </button>
        </div>
      </div>

      {mostrarForm && (
        <form onSubmit={(e) => void handleCrear(e)} className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 space-y-3">
          <div className="flex gap-4 flex-wrap">
            {[
              { id: 'u-nombre', label: 'Nombre', field: 'nombre' as const, type: 'text' },
              { id: 'u-apellido', label: 'Apellido', field: 'apellido' as const, type: 'text' },
              { id: 'u-email', label: 'Email', field: 'email' as const, type: 'email' },
              { id: 'u-password', label: 'Contraseña', field: 'password' as const, type: 'password' },
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
                  className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-44"
                />
              </div>
            ))}
            <div>
              <label className="block text-xs text-gray-600 mb-1">Modalidad cobro</label>
              <select
                value={form.modalidadCobro}
                onChange={(e) => setForm((p) => ({ ...p, modalidadCobro: e.target.value as 'factura' | 'liquidacion' }))}
                className="border border-gray-300 rounded-md px-2 py-1.5 text-sm"
              >
                <option value="liquidacion">Liquidación</option>
                <option value="factura">Factura</option>
              </select>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-2">Roles</p>
            <div className="flex flex-wrap gap-2">
              {ROLES_OPCIONES.map((rol) => (
                <label key={rol} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.roles.includes(rol)}
                    onChange={() => toggleRol(rol)}
                    className="rounded"
                  />
                  {rol}
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={crear.isPending} className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50">Guardar</button>
            <button type="button" onClick={() => setMostrarForm(false)} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-xs hover:bg-gray-50">Cancelar</button>
          </div>
        </form>
      )}

      {editError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
          {editError}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Email</th>
              <th className="py-2 pr-4">Roles</th>
              <th className="py-2 pr-4">Cobro</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="border-b border-gray-100">
                <td className="py-2 pr-4">{u.apellido}, {u.nombre}</td>
                <td className="py-2 pr-4 text-gray-500">{u.email}</td>
                <td className="py-2 pr-4">
                  <div className="flex flex-wrap gap-1">
                    {u.roles.map((r) => (
                      <span key={r} className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs">{r}</span>
                    ))}
                  </div>
                </td>
                <td className="py-2 pr-4 text-xs text-gray-500">{u.modalidadCobro}</td>
                <td className="py-2 pr-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {u.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    disabled={editar.isPending}
                    onClick={() => {
                      setEditError(null)
                      editar.mutateAsync({ id: u.id, payload: { activo: !u.activo } })
                        .catch((err: unknown) => {
                          const msg = err instanceof Error ? err.message : 'Error al actualizar usuario'
                          setEditError(msg)
                        })
                    }}
                    className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                  >
                    {u.activo ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
            {usuarios.length === 0 && (
              <tr><td colSpan={6} className="py-8 text-center text-gray-400 text-sm">Sin usuarios</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
