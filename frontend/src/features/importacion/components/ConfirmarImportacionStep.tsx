import type { Actividad } from '../types'

interface ConfirmarImportacionStepProps {
  actividadesSeleccionadas: Actividad[]
  umbral: number
  isConfirming: boolean
  onConfirmar: () => void
  onVolver: () => void
}

export function ConfirmarImportacionStep({
  actividadesSeleccionadas,
  umbral,
  isConfirming,
  onConfirmar,
  onVolver,
}: ConfirmarImportacionStepProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Paso 4: Confirmá la importación</h2>
      <div className="bg-gray-50 rounded-md p-4 mb-6 space-y-2">
        <p className="text-sm">
          <span className="font-medium">Actividades seleccionadas:</span>{' '}
          {actividadesSeleccionadas.length}
        </p>
        <ul className="text-sm text-gray-700 list-disc list-inside">
          {actividadesSeleccionadas.map((a) => (
            <li key={a.id}>{a.nombre}</li>
          ))}
        </ul>
        <p className="text-sm">
          <span className="font-medium">Umbral de aprobación:</span> {umbral}%
        </p>
      </div>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onVolver}
          disabled={isConfirming}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
        >
          Volver
        </button>
        <button
          type="button"
          onClick={onConfirmar}
          disabled={isConfirming}
          className="px-4 py-2 bg-green-600 text-white rounded-md text-sm disabled:opacity-50"
        >
          {isConfirming ? 'Importando…' : 'Confirmar importación'}
        </button>
      </div>
    </div>
  )
}
