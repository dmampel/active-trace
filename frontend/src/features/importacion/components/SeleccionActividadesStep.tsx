import type { Actividad } from '../types'

interface SeleccionActividadesStepProps {
  actividades: Actividad[]
  seleccionadas: string[]
  onChange: (ids: string[]) => void
  onContinuar: () => void
  onVolver: () => void
}

export function SeleccionActividadesStep({
  actividades,
  seleccionadas,
  onChange,
  onContinuar,
  onVolver,
}: SeleccionActividadesStepProps) {
  const todasSeleccionadas = actividades.length > 0 && seleccionadas.length === actividades.length
  const algunaSeleccionada = seleccionadas.length > 0

  const toggleMaestro = () => {
    if (todasSeleccionadas) {
      onChange([])
    } else {
      onChange(actividades.map((a) => a.id))
    }
  }

  const toggleActividad = (id: string) => {
    if (seleccionadas.includes(id)) {
      onChange(seleccionadas.filter((s) => s !== id))
    } else {
      onChange([...seleccionadas, id])
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Paso 2: Seleccioná las actividades</h2>
      <div className="mb-3">
        <label className="flex items-center gap-2 font-medium cursor-pointer">
          <input
            type="checkbox"
            checked={todasSeleccionadas}
            onChange={toggleMaestro}
            data-testid="checkbox-maestro"
          />
          Seleccionar todas
        </label>
      </div>
      <ul className="space-y-2 mb-6">
        {actividades.map((act) => (
          <li key={act.id}>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={seleccionadas.includes(act.id)}
                onChange={() => toggleActividad(act.id)}
                data-testid={`checkbox-act-${act.id}`}
              />
              <span>{act.nombre}</span>
              <span className="text-xs text-gray-500">({act.tipo})</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onVolver}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm"
        >
          Volver
        </button>
        <button
          type="button"
          onClick={onContinuar}
          disabled={!algunaSeleccionada}
          title={!algunaSeleccionada ? 'Seleccioná al menos una actividad' : undefined}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continuar
        </button>
      </div>
    </div>
  )
}
