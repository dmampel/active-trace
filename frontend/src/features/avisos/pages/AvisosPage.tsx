import { Link } from 'react-router-dom'
import { useAvisos, useToggleAvisoActivo } from '../hooks/useAvisos'
import type { Aviso, AvisoSeveridad } from '../types'

const SEVERIDAD_BADGE: Record<AvisoSeveridad, string> = {
  info: 'bg-blue-100 text-blue-700',
  advertencia: 'bg-yellow-100 text-yellow-700',
  critico: 'bg-red-100 text-red-700',
}

function AvisoRow({ aviso }: { aviso: Aviso }) {
  const toggle = useToggleAvisoActivo()

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-gray-900 font-medium">{aviso.titulo}</td>
      <td className="px-4 py-3 text-gray-500 capitalize">{aviso.scope}</td>
      <td className="px-4 py-3">
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERIDAD_BADGE[aviso.severidad]}`}>
          {aviso.severidad}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {aviso.vigenciaDesde}
        {aviso.vigenciaHasta ? ` → ${aviso.vigenciaHasta}` : ''}
      </td>
      <td className="px-4 py-3">
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            aviso.activo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {aviso.activo ? 'Activo' : 'Inactivo'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Link
            to={`/avisos/${aviso.id}/editar`}
            className="text-xs text-indigo-600 hover:underline"
          >
            Editar
          </Link>
          {aviso.requireAck && (
            <Link
              to={`/avisos/${aviso.id}/confirmaciones`}
              className="text-xs text-indigo-600 hover:underline"
            >
              Confirmaciones
            </Link>
          )}
          <button
            type="button"
            onClick={() => { void toggle.mutate({ id: aviso.id, activo: !aviso.activo }) }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {aviso.activo ? 'Desactivar' : 'Activar'}
          </button>
        </div>
      </td>
    </tr>
  )
}

export function AvisosPage() {
  const { data: avisos = [], isLoading } = useAvisos({ activo: true })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Avisos del Sistema</h1>
        <Link
          to="/avisos/nuevo"
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
          aria-label="Nuevo aviso"
        >
          + Nuevo aviso
        </Link>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Cargando avisos…</p>}

      {!isLoading && avisos.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin avisos activos</p>
          <p className="text-sm mt-1">Creá el primer aviso con el botón de arriba.</p>
        </div>
      )}

      {!isLoading && avisos.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Título
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Alcance
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Severidad
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Vigencia
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {avisos.map((a) => (
                <AvisoRow key={a.id} aviso={a} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
