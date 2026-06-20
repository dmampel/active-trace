import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getAtrasados } from '@/features/analisis/services/analisisApi'
import { getPreviewMensaje } from '../services/comunicacionApi'
import { useEnviarComunicacion } from '../hooks/useEnviarComunicacion'
import { useTracking } from '../hooks/useTracking'
import { PreviewComunicacionModal } from '../components/PreviewComunicacionModal'
import { TablaTracking } from '../components/TablaTracking'
import type { AlumnoAtrasado } from '@/features/analisis/types'
import type { PreviewMensaje } from '../types'

export function ComunicacionPage() {
  const { comisionId = '' } = useParams()
  const navigate = useNavigate()

  const [seleccionados, setSeleccionados] = useState<string[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [preview, setPreview] = useState<PreviewMensaje | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const { data: atrasados = [], isLoading } = useQuery({
    queryKey: ['analisis', comisionId, 'atrasados'],
    queryFn: () => getAtrasados(comisionId),
    enabled: !!comisionId,
  })

  const { mensajes } = useTracking(comisionId)
  const { enviar, isLoading: isEnviando, error: enviarError, reset: resetEnvio } = useEnviarComunicacion()

  const todosSeleccionados =
    atrasados.length > 0 && seleccionados.length === atrasados.length

  const toggleMaestro = () => {
    if (todosSeleccionados) {
      setSeleccionados([])
    } else {
      setSeleccionados(atrasados.map((a) => a.id))
    }
  }

  const toggleAlumno = (id: string) => {
    setSeleccionados((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    )
  }

  const handlePreview = async () => {
    setPreviewError(null)
    const primerDestinatario = atrasados.find((a) => seleccionados.includes(a.id))
    if (!primerDestinatario) return
    try {
      const data = await getPreviewMensaje(comisionId, primerDestinatario.id)
      setPreview(data)
      setModalOpen(true)
    } catch {
      setPreviewError('No se pudo obtener la vista previa del mensaje.')
    }
  }

  const handleEnviar = async () => {
    const destinatariosSeleccionados = atrasados
      .filter((a) => seleccionados.includes(a.id))
      .map((a: AlumnoAtrasado) => ({ alumnoId: a.id, nombre: a.nombre, email: a.email }))

    try {
      await enviar({ comisionId, destinatarios: destinatariosSeleccionados })
      setModalOpen(false)
      setSeleccionados([])
      navigate(`/comision/${comisionId}/comunicacion`)
    } catch {
      // error is handled by mutation state and shown in modal
    }
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    resetEnvio()
  }

  const errorMsg = enviarError?.response?.data?.detail ?? enviarError?.message ?? null

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Comunicaciones</h1>

      {/* Selección de destinatarios */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Alumnos atrasados</h2>
          <button
            type="button"
            onClick={() => void handlePreview()}
            disabled={seleccionados.length === 0}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previsualizar mensaje ({seleccionados.length})
          </button>
        </div>

        {previewError && <p className="text-sm text-red-600 mb-2">{previewError}</p>}

        {isLoading ? (
          <p className="text-sm text-gray-500">Cargando…</p>
        ) : atrasados.length === 0 ? (
          <p className="text-sm text-gray-500">No hay alumnos atrasados.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-600">
                <th className="py-2 pr-4 w-8">
                  <input
                    type="checkbox"
                    checked={todosSeleccionados}
                    onChange={toggleMaestro}
                    aria-label="Seleccionar todos"
                    data-testid="checkbox-maestro-com"
                  />
                </th>
                <th className="py-2 pr-4">Alumno</th>
                <th className="py-2 pr-4">Correo</th>
                <th className="py-2">Faltantes</th>
              </tr>
            </thead>
            <tbody>
              {atrasados.map((a) => (
                <tr key={a.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">
                    <input
                      type="checkbox"
                      checked={seleccionados.includes(a.id)}
                      onChange={() => toggleAlumno(a.id)}
                      aria-label={`Seleccionar ${a.nombre}`}
                    />
                  </td>
                  <td className="py-2 pr-4">
                    {a.apellido}, {a.nombre}
                  </td>
                  <td className="py-2 pr-4">{a.email}</td>
                  <td className="py-2">{a.actividadesFaltantes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Tracking */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Estado de mensajes</h2>
        <TablaTracking mensajes={mensajes} />
      </section>

      {/* Preview modal */}
      {modalOpen && preview && (
        <PreviewComunicacionModal
          preview={preview}
          totalDestinatarios={seleccionados.length}
          isEnviando={isEnviando}
          error={errorMsg}
          onEnviar={() => void handleEnviar()}
          onClose={handleCloseModal}
        />
      )}
    </div>
  )
}
