import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  umbral: z
    .number({ invalid_type_error: 'El umbral debe ser un número' })
    .min(1, 'El umbral debe ser al menos 1')
    .max(100, 'El umbral no puede superar 100'),
})

type UmbralForm = z.infer<typeof schema>

interface UmbralStepProps {
  umbralActual: number
  onContinuar: (umbral: number) => void
  onVolver: () => void
}

export function UmbralStep({ umbralActual, onContinuar, onVolver }: UmbralStepProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm<UmbralForm>({
    resolver: zodResolver(schema),
    defaultValues: { umbral: umbralActual },
    mode: 'onChange',
  })

  useEffect(() => {
    reset({ umbral: umbralActual })
  }, [umbralActual, reset])

  const onSubmit = (data: UmbralForm) => {
    onContinuar(data.umbral)
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Paso 3: Configurá el umbral de aprobación</h2>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mb-4">
          <label htmlFor="umbral" className="block text-sm font-medium text-gray-700 mb-1">
            Umbral de aprobación (%)
          </label>
          <input
            id="umbral"
            type="number"
            {...register('umbral', { valueAsNumber: true })}
            className="border border-gray-300 rounded-md px-3 py-2 w-32 text-sm"
            min={1}
            max={100}
          />
          {errors.umbral && (
            <p className="mt-1 text-sm text-red-600" role="alert">
              {errors.umbral.message}
            </p>
          )}
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onVolver}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm"
          >
            Volver
          </button>
          <button
            type="submit"
            disabled={!isValid}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continuar
          </button>
        </div>
      </form>
    </div>
  )
}
