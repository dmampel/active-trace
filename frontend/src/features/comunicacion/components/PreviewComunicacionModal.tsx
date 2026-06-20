import type { PreviewMensaje } from '../types'

interface PreviewComunicacionModalProps {
  preview: PreviewMensaje
  totalDestinatarios: number
  isEnviando: boolean
  error: string | null
  onEnviar: () => void
  onClose: () => void
}

export function PreviewComunicacionModal({
  preview,
  totalDestinatarios,
  isEnviando,
  error,
  onEnviar,
  onClose,
}: PreviewComunicacionModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-title"
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
        <div className="p-6 border-b border-gray-200">
          <h3 id="preview-title" className="text-lg font-semibold">
            Vista previa del mensaje
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Se enviará a {totalDestinatarios} destinatario
            {totalDestinatarios !== 1 ? 's' : ''}. Mostrando el mensaje del primero.
          </p>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Asunto</p>
            <p className="text-sm font-medium">{preview.asunto}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Cuerpo</p>
            <div className="bg-gray-50 rounded p-3 text-sm whitespace-pre-wrap">{preview.cuerpo}</div>
          </div>
          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>
        <div className="p-6 border-t border-gray-200 flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={isEnviando}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm disabled:opacity-50"
          >
            Cerrar
          </button>
          <button
            type="button"
            onClick={onEnviar}
            disabled={isEnviando}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm disabled:opacity-50"
          >
            {isEnviando ? 'Enviando…' : 'Confirmar envío'}
          </button>
        </div>
      </div>
    </div>
  )
}
