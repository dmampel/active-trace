import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAsignacionMasiva } from '../hooks/useEquipos'
import type { AsignacionMasivaItem, RolEquipo } from '../types'

const schema = z.object({
  materiaId: z.string().min(1, 'Materia requerida'),
  cohorteId: z.string().min(1, 'Cohorte requerida'),
  carreraId: z.string().min(1, 'Carrera requerida'),
  rol: z.enum(['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR'] as const, {
    errorMap: () => ({ message: 'Rol requerido' }),
  }),
  vigenciaDesde: z.string().min(1, 'Vigencia desde requerida'),
  vigenciaHasta: z.string().optional(),
  docentesRaw: z.string().min(1, 'Ingresá al menos un ID de docente'),
})

type FormValues = z.infer<typeof schema>

const ROLES: RolEquipo[] = ['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR']

export function AsignacionMasivaPage() {
  const [resultados, setResultados] = useState<AsignacionMasivaItem[]>([])
  const mutation = useAsignacionMasiva()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    const docenteIds = values.docentesRaw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    const result = await mutation.mutateAsync({
      docenteIds,
      materiaId: values.materiaId,
      carreraId: values.carreraId,
      cohorteId: values.cohorteId,
      rol: values.rol,
      vigenciaDesde: values.vigenciaDesde,
      vigenciaHasta: values.vigenciaHasta,
    })
    setResultados(result)
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Asignación Masiva</h1>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <label htmlFor="materiaId" className="block text-sm font-medium text-gray-700 mb-1">
            Materia
          </label>
          <input
            id="materiaId"
            {...register('materiaId')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
            placeholder="ID de materia"
          />
          {errors.materiaId && (
            <p className="text-red-600 text-xs mt-1">{errors.materiaId.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="carreraId" className="block text-sm font-medium text-gray-700 mb-1">
            Carrera
          </label>
          <input
            id="carreraId"
            {...register('carreraId')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
            placeholder="ID de carrera"
          />
          {errors.carreraId && (
            <p className="text-red-600 text-xs mt-1">{errors.carreraId.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="cohorteId" className="block text-sm font-medium text-gray-700 mb-1">
            Cohorte
          </label>
          <input
            id="cohorteId"
            {...register('cohorteId')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
            placeholder="ID de cohorte"
          />
          {errors.cohorteId && (
            <p className="text-red-600 text-xs mt-1">{errors.cohorteId.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="rol" className="block text-sm font-medium text-gray-700 mb-1">
            Rol
          </label>
          <select
            id="rol"
            {...register('rol')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          >
            <option value="">Seleccioná un rol…</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          {errors.rol && <p className="text-red-600 text-xs mt-1">{errors.rol.message}</p>}
        </div>

        <div>
          <label htmlFor="vigenciaDesde" className="block text-sm font-medium text-gray-700 mb-1">
            Vigencia desde
          </label>
          <input
            id="vigenciaDesde"
            type="date"
            {...register('vigenciaDesde')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          />
          {errors.vigenciaDesde && (
            <p className="text-red-600 text-xs mt-1">{errors.vigenciaDesde.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="docentesRaw" className="block text-sm font-medium text-gray-700 mb-1">
            Docentes (IDs separados por coma)
          </label>
          <input
            id="docentesRaw"
            {...register('docentesRaw')}
            placeholder="ID del docente"
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          />
          {errors.docentesRaw && (
            <p className="text-red-600 text-xs mt-1">{errors.docentesRaw.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          aria-label="Asignar"
        >
          {mutation.isPending ? 'Procesando…' : 'Asignar'}
        </button>
      </form>

      {/* Results table */}
      {resultados.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Resultados</h2>
          <table className="w-full text-sm border-collapse">
            <thead className="bg-gray-50">
              <tr>
                <th className="border border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-600">
                  Docente ID
                </th>
                <th className="border border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-600">
                  Resultado
                </th>
                <th className="border border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-600">
                  Detalle
                </th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r) => (
                <tr
                  key={r.docenteId}
                  className={r.resultado === 'error' ? 'bg-red-50' : 'bg-green-50'}
                >
                  <td className="border border-gray-200 px-3 py-2">{r.docenteId}</td>
                  <td className="border border-gray-200 px-3 py-2 font-medium">
                    {r.resultado === 'ok' ? '✓ OK' : '✗ Error'}
                  </td>
                  <td className="border border-gray-200 px-3 py-2 text-red-600">
                    {r.mensaje ?? '—'}
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
