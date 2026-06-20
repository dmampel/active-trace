import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { avisoSchema, type AvisoFormSchema } from './avisoSchema'
import type { Aviso, AvisoRol } from '../types'

const ROLES: AvisoRol[] = ['PROFESOR', 'TUTOR', 'NEXO', 'COORDINADOR', 'ADMIN', 'ALUMNO']

interface AvisoFormProps {
  defaultValues?: Partial<AvisoFormSchema>
  onSubmit: (data: AvisoFormSchema) => Promise<void>
  isSubmitting?: boolean
}

export function AvisoForm({ defaultValues, onSubmit, isSubmitting }: AvisoFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors },
  } = useForm<AvisoFormSchema>({
    resolver: zodResolver(avisoSchema),
    defaultValues: {
      scope: 'global',
      roles: [],
      severidad: 'info',
      orden: 0,
      requireAck: false,
      ...defaultValues,
    },
  })

  const scope = watch('scope')

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5 max-w-xl">
      {/* Scope */}
      <div>
        <label htmlFor="scope" className="block text-sm font-medium text-gray-700 mb-1">
          Alcance
        </label>
        <select
          id="scope"
          {...register('scope')}
          className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
        >
          <option value="global">Global</option>
          <option value="materia">Materia</option>
          <option value="cohorte">Cohorte</option>
        </select>
        {errors.scope && <p className="text-red-600 text-xs mt-1">{errors.scope.message}</p>}
      </div>

      {/* Materia — shown for scope materia or cohorte */}
      {(scope === 'materia' || scope === 'cohorte') && (
        <div>
          <label htmlFor="materiaId" className="block text-sm font-medium text-gray-700 mb-1">
            Materia
          </label>
          <input
            id="materiaId"
            {...register('materiaId')}
            placeholder="ID de materia"
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          />
          {errors.materiaId && (
            <p className="text-red-600 text-xs mt-1">{errors.materiaId.message}</p>
          )}
        </div>
      )}

      {/* Cohorte — shown only for scope cohorte */}
      {scope === 'cohorte' && (
        <div>
          <label htmlFor="cohorteId" className="block text-sm font-medium text-gray-700 mb-1">
            Cohorte
          </label>
          <input
            id="cohorteId"
            {...register('cohorteId')}
            placeholder="ID de cohorte"
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          />
          {errors.cohorteId && (
            <p className="text-red-600 text-xs mt-1">{errors.cohorteId.message}</p>
          )}
        </div>
      )}

      {/* Roles */}
      <div>
        <fieldset>
          <legend className="block text-sm font-medium text-gray-700 mb-1">Roles destinatarios</legend>
          <div className="flex flex-wrap gap-3">
            {ROLES.map((rol) => (
              <label key={rol} className="flex items-center gap-1 text-sm text-gray-700">
                <Controller
                  name="roles"
                  control={control}
                  render={({ field }) => (
                    <input
                      type="checkbox"
                      value={rol}
                      checked={field.value?.includes(rol)}
                      onChange={(e) => {
                        const current = field.value ?? []
                        if (e.target.checked) {
                          field.onChange([...current, rol])
                        } else {
                          field.onChange(current.filter((r: string) => r !== rol))
                        }
                      }}
                    />
                  )}
                />
                {rol}
              </label>
            ))}
          </div>
          {errors.roles && <p className="text-red-600 text-xs mt-1">{errors.roles.message}</p>}
        </fieldset>
      </div>

      {/* Severidad */}
      <div>
        <label htmlFor="severidad" className="block text-sm font-medium text-gray-700 mb-1">
          Severidad
        </label>
        <select
          id="severidad"
          {...register('severidad')}
          className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
        >
          <option value="info">Info</option>
          <option value="advertencia">Advertencia</option>
          <option value="critico">Crítico</option>
        </select>
      </div>

      {/* Titulo */}
      <div>
        <label htmlFor="titulo" className="block text-sm font-medium text-gray-700 mb-1">
          Título
        </label>
        <input
          id="titulo"
          {...register('titulo')}
          className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          placeholder="Título del aviso"
        />
        {errors.titulo && <p className="text-red-600 text-xs mt-1">{errors.titulo.message}</p>}
      </div>

      {/* Cuerpo */}
      <div>
        <label htmlFor="cuerpo" className="block text-sm font-medium text-gray-700 mb-1">
          Cuerpo
        </label>
        <textarea
          id="cuerpo"
          {...register('cuerpo')}
          rows={4}
          className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          placeholder="Contenido del aviso"
        />
        {errors.cuerpo && <p className="text-red-600 text-xs mt-1">{errors.cuerpo.message}</p>}
      </div>

      {/* Vigencia */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label htmlFor="vigenciaDesde" className="block text-sm font-medium text-gray-700 mb-1">
            Desde
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
        <div className="flex-1">
          <label htmlFor="vigenciaHasta" className="block text-sm font-medium text-gray-700 mb-1">
            Hasta (opcional)
          </label>
          <input
            id="vigenciaHasta"
            type="date"
            {...register('vigenciaHasta')}
            className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          />
        </div>
      </div>

      {/* Orden */}
      <div>
        <label htmlFor="orden" className="block text-sm font-medium text-gray-700 mb-1">
          Orden de prioridad
        </label>
        <input
          id="orden"
          type="number"
          {...register('orden', { valueAsNumber: true })}
          className="border border-gray-300 rounded-md px-3 py-2 w-full text-sm"
          defaultValue={0}
        />
      </div>

      {/* Require Ack */}
      <div className="flex items-center gap-2">
        <input id="requireAck" type="checkbox" {...register('requireAck')} />
        <label htmlFor="requireAck" className="text-sm text-gray-700">
          Requiere confirmación de lectura
        </label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        aria-label="Guardar"
      >
        {isSubmitting ? 'Guardando…' : 'Guardar aviso'}
      </button>
    </form>
  )
}

// Helper to convert Aviso to form defaults
export function avisoToFormDefaults(aviso: Aviso): Partial<AvisoFormSchema> {
  return {
    scope: aviso.scope,
    roles: aviso.roles as AvisoRol[],
    severidad: aviso.severidad,
    titulo: aviso.titulo,
    cuerpo: aviso.cuerpo,
    vigenciaDesde: aviso.vigenciaDesde,
    vigenciaHasta: aviso.vigenciaHasta ?? undefined,
    orden: aviso.orden,
    requireAck: aviso.requireAck,
    materiaId: aviso.materiaId,
    cohorteId: aviso.cohorteId,
  }
}
