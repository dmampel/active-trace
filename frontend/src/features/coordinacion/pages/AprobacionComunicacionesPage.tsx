import {
  useAprobacionComunicaciones,
  useAprobarMensaje,
  useCancelarMensaje,
  useAprobarLote,
} from '../hooks/useCoordinacion'

export function AprobacionComunicacionesPage() {
  const { mensajes, isLoading } = useAprobacionComunicaciones()
  const aprobarMensaje = useAprobarMensaje()
  const cancelarMensaje = useCancelarMensaje()
  const aprobarLote = useAprobarLote()

  const mensajesIds = mensajes.map((m) => m.id)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Cola de Aprobación de Comunicaciones</h1>
        {mensajes.length > 0 && (
          <button
            type="button"
            onClick={() => { void aprobarLote.mutate(mensajesIds) }}
            disabled={aprobarLote.isPending}
            className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            aria-label="Aprobar lote"
          >
            {aprobarLote.isPending ? 'Aprobando…' : `Aprobar lote (${mensajes.length})`}
          </button>
        )}
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Cargando cola de aprobación…</p>}

      {!isLoading && mensajes.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Sin mensajes pendientes</p>
          <p className="text-sm mt-1">
            No hay mensajes en espera de aprobación. El monitoreo automático está pausado.
          </p>
        </div>
      )}

      {!isLoading && mensajes.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Asunto
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Destinatario
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Emisor
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Creado
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {mensajes.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900 font-medium">{m.asunto}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {m.destinatarioNombre} {m.destinatarioApellido}
                    <div className="text-xs text-gray-400">{m.destinatarioEmail}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {m.emisorNombre} {m.emisorApellido}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {new Date(m.creadoEn).toLocaleString('es-AR')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { void aprobarMensaje.mutate(m.id) }}
                        disabled={aprobarMensaje.isPending}
                        className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50"
                        aria-label={`Aprobar ${m.id}`}
                      >
                        Aprobar
                      </button>
                      <button
                        type="button"
                        onClick={() => { void cancelarMensaje.mutate(m.id) }}
                        disabled={cancelarMensaje.isPending}
                        className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                        aria-label={`Cancelar ${m.id}`}
                      >
                        Cancelar
                      </button>
                    </div>
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
