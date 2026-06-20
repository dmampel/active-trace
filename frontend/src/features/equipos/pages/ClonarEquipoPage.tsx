import { useReducer } from 'react'
import { useClonarEquipo } from '../hooks/useEquipos'
import type { ClonarEquipoResult } from '../types'

interface State {
  step: 1 | 2 | 3
  origen: { materiaId: string; carreraId: string; cohorteId: string }
  destino: { materiaId: string; carreraId: string; cohorteId: string }
  error: string | null
  result: ClonarEquipoResult | null
  origenError: string | null
}

type Action =
  | { type: 'SET_ORIGEN'; payload: Partial<State['origen']> }
  | { type: 'SET_DESTINO'; payload: Partial<State['destino']> }
  | { type: 'NEXT'; origenError?: string }
  | { type: 'PREV' }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'SET_RESULT'; result: ClonarEquipoResult }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_ORIGEN':
      return { ...state, origen: { ...state.origen, ...action.payload } }
    case 'SET_DESTINO':
      return { ...state, destino: { ...state.destino, ...action.payload } }
    case 'NEXT':
      if (action.origenError) return { ...state, origenError: action.origenError }
      return { ...state, step: (state.step < 3 ? state.step + 1 : 3) as 1 | 2 | 3, origenError: null }
    case 'PREV':
      return { ...state, step: (state.step > 1 ? state.step - 1 : 1) as 1 | 2 | 3, error: null }
    case 'SET_ERROR':
      return { ...state, error: action.error }
    case 'SET_RESULT':
      return { ...state, result: action.result, error: null }
    default:
      return state
  }
}

const initialState: State = {
  step: 1,
  origen: { materiaId: '', carreraId: '', cohorteId: '' },
  destino: { materiaId: '', carreraId: '', cohorteId: '' },
  error: null,
  result: null,
  origenError: null,
}

export function ClonarEquipoPage() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const mutation = useClonarEquipo()

  function handleNextFromStep1() {
    const { materiaId, carreraId, cohorteId } = state.origen
    if (!materiaId || !carreraId || !cohorteId) {
      dispatch({ type: 'NEXT', origenError: 'Completá todos los campos de origen: materia, carrera y cohorte son obligatorios.' })
      return
    }
    dispatch({ type: 'NEXT' })
  }

  async function handleConfirm() {
    try {
      const result = await mutation.mutateAsync({
        origenMateriaId: state.origen.materiaId,
        origenCarreraId: state.origen.carreraId,
        origenCohorteId: state.origen.cohorteId,
        destinoMateriaId: state.destino.materiaId,
        destinoCarreraId: state.destino.carreraId,
        destinoCohorteId: state.destino.cohorteId,
      })
      dispatch({ type: 'SET_RESULT', result })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al clonar el equipo.'
      dispatch({ type: 'SET_ERROR', error: msg })
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Clonar Equipo Docente</h1>

      {/* Stepper header */}
      <div className="flex items-center gap-2 mb-8">
        {([1, 2, 3] as const).map((n) => (
          <div key={n} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                state.step === n
                  ? 'bg-indigo-600 text-white'
                  : state.step > n
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-500'
              }`}
            >
              {n}
            </div>
            {n < 3 && <div className="w-8 h-0.5 bg-gray-200" />}
          </div>
        ))}
      </div>

      {/* Step 1 — Origen */}
      {state.step === 1 && (
        <div>
          <p className="text-sm text-gray-600 mb-4 font-medium">Paso 1: Seleccioná el equipo origen</p>
          <div className="space-y-3">
            <div>
              <label htmlFor="materia-origen" className="block text-sm font-medium text-gray-700 mb-1">
                Materia origen
              </label>
              <input
                id="materia-origen"
                value={state.origen.materiaId}
                onChange={(e) => { dispatch({ type: 'SET_ORIGEN', payload: { materiaId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de materia"
              />
            </div>
            <div>
              <label htmlFor="carrera-origen" className="block text-sm font-medium text-gray-700 mb-1">
                Carrera origen
              </label>
              <input
                id="carrera-origen"
                value={state.origen.carreraId}
                onChange={(e) => { dispatch({ type: 'SET_ORIGEN', payload: { carreraId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de carrera"
              />
            </div>
            <div>
              <label htmlFor="cohorte-origen" className="block text-sm font-medium text-gray-700 mb-1">
                Cohorte origen
              </label>
              <input
                id="cohorte-origen"
                value={state.origen.cohorteId}
                onChange={(e) => { dispatch({ type: 'SET_ORIGEN', payload: { cohorteId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de cohorte"
              />
            </div>
          </div>
          {state.origenError && (
            <p className="text-red-600 text-sm mt-3">{state.origenError}</p>
          )}
          <button
            type="button"
            onClick={handleNextFromStep1}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
            aria-label="Siguiente"
          >
            Siguiente
          </button>
        </div>
      )}

      {/* Step 2 — Destino */}
      {state.step === 2 && (
        <div>
          <p className="text-sm text-gray-600 mb-4 font-medium">Paso 2: Seleccioná el equipo destino</p>
          <div className="space-y-3">
            <div>
              <label htmlFor="materia-destino" className="block text-sm font-medium text-gray-700 mb-1">
                Materia destino
              </label>
              <input
                id="materia-destino"
                value={state.destino.materiaId}
                onChange={(e) => { dispatch({ type: 'SET_DESTINO', payload: { materiaId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de materia"
              />
            </div>
            <div>
              <label htmlFor="carrera-destino" className="block text-sm font-medium text-gray-700 mb-1">
                Carrera destino
              </label>
              <input
                id="carrera-destino"
                value={state.destino.carreraId}
                onChange={(e) => { dispatch({ type: 'SET_DESTINO', payload: { carreraId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de carrera"
              />
            </div>
            <div>
              <label htmlFor="cohorte-destino" className="block text-sm font-medium text-gray-700 mb-1">
                Cohorte destino
              </label>
              <input
                id="cohorte-destino"
                value={state.destino.cohorteId}
                onChange={(e) => { dispatch({ type: 'SET_DESTINO', payload: { cohorteId: e.target.value } }) }}
                className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
                placeholder="ID de cohorte"
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={() => { dispatch({ type: 'PREV' }) }}
              className="px-4 py-2 border border-gray-300 text-gray-600 rounded-md text-sm font-medium hover:bg-gray-50"
            >
              Atrás
            </button>
            <button
              type="button"
              onClick={() => { dispatch({ type: 'NEXT' }) }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
              aria-label="Siguiente"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Step 3 — Confirmación */}
      {state.step === 3 && (
        <div>
          <p className="text-sm text-gray-600 mb-4 font-medium">Paso 3: Confirmación</p>
          <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm space-y-2">
            <div>
              <span className="font-medium text-gray-700">Origen:</span>{' '}
              Materia {state.origen.materiaId} / Carrera {state.origen.carreraId} / Cohorte {state.origen.cohorteId}
            </div>
            <div>
              <span className="font-medium text-gray-700">Destino:</span>{' '}
              Materia {state.destino.materiaId} / Carrera {state.destino.carreraId} / Cohorte {state.destino.cohorteId}
            </div>
          </div>

          {state.error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              {state.error}
            </div>
          )}

          {state.result && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-700">
              Se crearon {state.result.asignacionesCreadas} asignaciones exitosamente.
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => { dispatch({ type: 'PREV' }) }}
              className="px-4 py-2 border border-gray-300 text-gray-600 rounded-md text-sm font-medium hover:bg-gray-50"
            >
              Atrás
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={mutation.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              aria-label="Confirmar"
            >
              {mutation.isPending ? 'Clonando…' : 'Confirmar clonado'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
