import { useState, useRef, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useImportarCalificaciones } from '../hooks/useImportarCalificaciones'
import { SeleccionActividadesStep } from '../components/SeleccionActividadesStep'
import { UmbralStep } from '../components/UmbralStep'
import { ConfirmarImportacionStep } from '../components/ConfirmarImportacionStep'
import { ConfirmarSalidaWizard } from '../components/ConfirmarSalidaWizard'
import type { WizardStep, Actividad } from '../types'

const TOTAL_STEPS = 4

export function ImportarCalificacionesPage() {
  const { comisionId = '' } = useParams()
  const navigate = useNavigate()

  const [step, setStep] = useState<WizardStep>(1)
  const [actividadesSeleccionadas, setActividadesSeleccionadas] = useState<string[]>([])
  const [umbral, setUmbral] = useState(60)
  const [mostrarSalida, setMostrarSalida] = useState(false)
  const pendingNavRef = useRef<string | null>(null)

  const {
    uploadProgress,
    preview,
    uploadError,
    isUploading,
    isConfirming,
    confirmError,
    upload,
    confirmar,
    reset,
  } = useImportarCalificaciones()

  // Warn on tab/window close when in steps 2-4
  useEffect(() => {
    if (step >= 2) {
      const handler = (e: BeforeUnloadEvent) => {
        e.preventDefault()
      }
      window.addEventListener('beforeunload', handler)
      return () => window.removeEventListener('beforeunload', handler)
    }
  }, [step])

  // Initialize all actividades as selected when preview arrives
  useEffect(() => {
    if (preview?.actividades) {
      setActividadesSeleccionadas(preview.actividades.map((a) => a.id))
    }
  }, [preview])

  const handleFileSelected = async (file: File) => {
    try {
      await upload(comisionId, file)
      setStep(2)
    } catch (e) {
      // Error is handled by the hook and displayed in the UI
    }
  }

  const handleActividadesContinuar = () => {
    setStep(3)
  }

  const handleUmbralContinuar = (val: number) => {
    setUmbral(val)
    setStep(4)
  }

  const handleConfirmar = async () => {
    await confirmar(comisionId, {
      actividadesIds: actividadesSeleccionadas,
      umbral,
    })
    navigate(`/comision/${comisionId}/analisis`)
  }

  const handleVolver = () => {
    setStep((prev) => (prev > 1 ? ((prev - 1) as WizardStep) : 1))
  }

  const handleNavigateAway = () => {
    if (step >= 2) {
      setMostrarSalida(true)
    } else {
      navigate('/')
    }
  }

  const handleConfirmarSalida = () => {
    setMostrarSalida(false)
    reset()
    if (pendingNavRef.current) {
      navigate(pendingNavRef.current)
    } else {
      navigate('/')
    }
  }

  const actividadesConInfo: Actividad[] = preview?.actividades ?? []
  const actividadesSeleccionadasInfo = actividadesConInfo.filter((a) =>
    actividadesSeleccionadas.includes(a.id),
  )

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Importar calificaciones</h1>
        <button
          type="button"
          onClick={handleNavigateAway}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancelar
        </button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8" aria-label="Progreso del wizard">
        {([1, 2, 3, 4] as WizardStep[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                s === step
                  ? 'bg-indigo-600 text-white'
                  : s < step
                    ? 'bg-indigo-200 text-indigo-700'
                    : 'bg-gray-200 text-gray-500'
              }`}
            >
              {s}
            </div>
            {s < TOTAL_STEPS && <div className="w-8 h-0.5 bg-gray-300" />}
          </div>
        ))}
        <span className="text-sm text-gray-500 ml-2">
          Paso {step} de {TOTAL_STEPS}
        </span>
      </div>

      {/* Step 1: Upload */}
      {step === 1 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Paso 1: Subí el archivo de calificaciones</h2>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={isUploading}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void handleFileSelected(file)
            }}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            data-testid="file-input"
          />
          {isUploading && (
            <div className="mt-4" aria-label="Progreso de carga">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Subiendo archivo…</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
          {uploadError && (
            <p className="mt-3 text-sm text-red-600" role="alert">
              {uploadError}
            </p>
          )}
        </div>
      )}

      {/* Step 2: Select activities */}
      {step === 2 && preview && (
        <SeleccionActividadesStep
          actividades={actividadesConInfo}
          seleccionadas={actividadesSeleccionadas}
          onChange={setActividadesSeleccionadas}
          onContinuar={handleActividadesContinuar}
          onVolver={handleVolver}
        />
      )}

      {/* Step 3: Set threshold */}
      {step === 3 && (
        <UmbralStep
          umbralActual={umbral}
          onContinuar={handleUmbralContinuar}
          onVolver={handleVolver}
        />
      )}

      {/* Step 4: Confirm */}
      {step === 4 && (
        <ConfirmarImportacionStep
          actividadesSeleccionadas={actividadesSeleccionadasInfo}
          umbral={umbral}
          isConfirming={isConfirming}
          onConfirmar={() => void handleConfirmar()}
          onVolver={handleVolver}
        />
      )}

      {confirmError && (
        <p className="mt-4 text-sm text-red-600" role="alert">
          {confirmError}
        </p>
      )}

      <ConfirmarSalidaWizard
        open={mostrarSalida}
        onConfirmar={handleConfirmarSalida}
        onCancelar={() => setMostrarSalida(false)}
      />
    </div>
  )
}
