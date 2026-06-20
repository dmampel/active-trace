import { useState } from 'react'
import { useVaciarComision } from '../hooks/useVaciarComision'

interface VaciarDatosButtonProps {
  comisionId: string
}

export function VaciarDatosButton({ comisionId }: VaciarDatosButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const { vaciar, isLoading } = useVaciarComision(comisionId)

  const handleConfirmar = async () => {
    await vaciar()
    setDialogOpen(false)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        className="px-3 py-1.5 text-sm text-red-600 border border-red-300 rounded-md hover:bg-red-50"
      >
        Vaciar datos de la comisión
      </button>

      {dialogOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="vaciar-title"
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
        >
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 id="vaciar-title" className="text-lg font-semibold mb-2 text-red-700">
              ¿Vaciar datos?
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              Esta acción eliminará todas las calificaciones importadas de la comisión. No se puede
              deshacer.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setDialogOpen(false)}
                disabled={isLoading}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmar()}
                disabled={isLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm disabled:opacity-50"
              >
                {isLoading ? 'Vaciando…' : 'Sí, vaciar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
