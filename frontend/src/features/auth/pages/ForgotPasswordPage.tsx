import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { useForgotPassword } from '@/features/auth/hooks/useForgotPassword'

const schema = z.object({
  email: z.string().min(1, 'El email es requerido').email('Email inválido'),
})

type ForgotFormData = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const { forgotPassword, isLoading, sent } = useForgotPassword()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotFormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: ForgotFormData) => {
    void forgotPassword(data.email)
  }

  if (sent) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md text-center">
          <div className="mb-4 text-5xl">📧</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Revisá tu casilla</h2>
          <p className="text-gray-600 text-sm">
            Si tu email está registrado, recibirás un enlace para restablecer tu contraseña.
          </p>
          <Link to="/login" className="mt-6 inline-block text-sm text-indigo-600 hover:underline">
            Volver al login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Recuperar contraseña</h1>
          <p className="mt-2 text-gray-600 text-sm">
            Ingresá tu email y te enviamos un enlace de recuperación.
          </p>
        </div>

        <div className="rounded-lg bg-white p-8 shadow-md">
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...register('email')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              {errors.email && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {isLoading ? 'Enviando…' : 'Enviar enlace'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <Link to="/login" className="text-sm text-indigo-600 hover:underline">
              Volver al login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
