import { useRef, useEffect, type MutableRefObject } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useLocation, Navigate } from 'react-router-dom'
import { useVerify2fa } from '@/features/auth/hooks/useVerify2fa'

const tfaSchema = z.object({
  code: z
    .string()
    .length(6, 'El código debe tener 6 dígitos')
    .regex(/^\d+$/, 'Solo se permiten dígitos'),
})

type TfaFormData = z.infer<typeof tfaSchema>

interface LocationState {
  temp_token?: string
}

export function TwoFactorPage() {
  const location = useLocation()
  const state = location.state as LocationState | null
  const tempToken = state?.temp_token

  const { verify, isLoading, error } = useVerify2fa()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<TfaFormData>({
    resolver: zodResolver(tfaSchema),
  })

  const code = watch('code', '')
  const { ref: rhfRef, ...rest } = register('code')

  // Auto-submit when 6 digits entered
  useEffect(() => {
    if (code?.length === 6) {
      void handleSubmit(onSubmit)()
    }
  }, [code]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!tempToken) {
    return <Navigate to="/login" replace />
  }

  const onSubmit = (data: TfaFormData) => {
    void verify(tempToken, data.code)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Verificación en 2 pasos</h1>
          <p className="mt-2 text-gray-600">Ingresá el código de tu aplicación autenticadora</p>
        </div>

        <div className="rounded-lg bg-white p-8 shadow-md">
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="mb-6">
              <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
                Código TOTP (6 dígitos)
              </label>
              <input
                id="code"
                type="text"
                inputMode="numeric"
                maxLength={6}
                {...rest}
                ref={(el) => {
                  rhfRef(el)
                  ;(inputRef as MutableRefObject<HTMLInputElement | null>).current = el
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-center text-xl tracking-widest focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                aria-invalid={errors.code ? 'true' : 'false'}
              />
              {errors.code && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors.code.message}
                </p>
              )}
            </div>

            {error && (
              <div role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {isLoading ? 'Verificando…' : 'Verificar código'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
