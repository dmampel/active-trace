import { useParams, Navigate } from 'react-router-dom'
import { useAviso, useConfirmacionesAviso } from '../hooks/useAvisos'

export function ConfirmacionesAvisoPage() {
  const { id } = useParams<{ id: string }>()
  const { data: aviso, isLoading: loadingAviso } = useAviso(id ?? '')
  const { data: confirmaciones = [], isLoading: loadingConf } = useConfirmacionesAviso(id ?? '')

  if (loadingAviso) return <p className="text-gray-500">Cargando aviso…</p>

  // Redirect if aviso doesn't require ack
  if (aviso && !aviso.requireAck) {
    return <Navigate to="/avisos" replace />
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Confirmaciones de lectura</h1>
      {aviso && (
        <p className="text-gray-500 text-sm mb-6">
          Aviso: <span className="font-medium text-gray-700">{aviso.titulo}</span>
        </p>
      )}

      {loadingConf && <p className="text-gray-500 text-sm">Cargando confirmaciones…</p>}

      {!loadingConf && confirmaciones.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Nadie confirmó la lectura aún</p>
          <p className="text-sm mt-1">Las confirmaciones aparecerán aquí a medida que los usuarios lean el aviso.</p>
        </div>
      )}

      {!loadingConf && confirmaciones.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <p className="text-sm font-medium text-gray-700">
              {confirmaciones.length} usuario{confirmaciones.length !== 1 ? 's' : ''} confirmaron la lectura
            </p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Usuario
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Confirmado el
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {confirmaciones.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">
                    {c.userNombre} {c.userApellido}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{c.userEmail}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(c.confirmedAt).toLocaleString('es-AR')}
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
