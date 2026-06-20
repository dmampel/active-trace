import type { MensajeTracking, MensajeEstado } from '../types'

const BADGE_COLORS: Record<MensajeEstado, string> = {
  Pendiente: 'bg-gray-100 text-gray-600',
  Enviando: 'bg-yellow-100 text-yellow-700',
  OK: 'bg-green-100 text-green-700',
  Fallido: 'bg-red-100 text-red-700',
  Cancelado: 'bg-orange-100 text-orange-700',
}

interface TablaTrackingProps {
  mensajes: MensajeTracking[]
}

export function TablaTracking({ mensajes }: TablaTrackingProps) {
  if (mensajes.length === 0) {
    return (
      <p className="text-sm text-gray-500" data-testid="tracking-empty">
        Aún no hay mensajes enviados para esta comisión
      </p>
    )
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b border-gray-200 text-left text-gray-600">
          <th className="py-2 pr-4">Destinatario</th>
          <th className="py-2 pr-4">Estado</th>
          <th className="py-2">Actualizado</th>
        </tr>
      </thead>
      <tbody>
        {mensajes.map((m) => (
          <tr key={m.id} className="border-b border-gray-100">
            <td className="py-2 pr-4">
              {m.destinatarioNombre} ({m.destinatarioEmail})
            </td>
            <td className="py-2 pr-4">
              <span
                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${BADGE_COLORS[m.estado as MensajeEstado] ?? 'bg-gray-100 text-gray-600'}`}
              >
                {m.estado}
              </span>
            </td>
            <td className="py-2 text-gray-500">
              {new Date(m.timestamp).toLocaleString('es-AR')}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
