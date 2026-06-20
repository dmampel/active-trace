interface ConfirmarSalidaWizardProps {
  open: boolean
  onConfirmar: () => void
  onCancelar: () => void
}

export function ConfirmarSalidaWizard({ open, onConfirmar, onCancelar }: ConfirmarSalidaWizardProps) {
  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="salida-title"
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 id="salida-title" className="text-lg font-semibold mb-2">
          ¿Abandonar el wizard?
        </h3>
        <p className="text-sm text-gray-600 mb-6">
          Si salís ahora, perdés los datos ingresados hasta el momento.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancelar}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirmar}
            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm"
          >
            Salir igual
          </button>
        </div>
      </div>
    </div>
  )
}
