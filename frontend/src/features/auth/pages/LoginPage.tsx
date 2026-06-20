import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { useLogin } from '@/features/auth/hooks/useLogin'
import { apiClient } from '@/shared/services/api'
import { tokenStorage } from '@/shared/services/tokenStorage'

const loginSchema = z.object({
  email: z.string().min(1, 'El email es requerido').email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

type LoginFormData = z.infer<typeof loginSchema>

const DEV_USERS = [
  { label: 'ADMIN', email: 'admin@trace.utn.edu.ar' },
  { label: 'COORDINADOR', email: 'coordinador@trace.utn.edu.ar' },
  { label: 'NEXO', email: 'nexo@trace.utn.edu.ar' },
  { label: 'PROFESOR', email: 'profesor@trace.utn.edu.ar' },
  { label: 'TUTOR', email: 'tutor@trace.utn.edu.ar' },
  { label: 'FINANZAS', email: 'finanzas@trace.utn.edu.ar' },
  { label: 'ALUMNO', email: 'alumno@trace.utn.edu.ar' },
]

export function LoginPage() {
  const { login, isLoading, error } = useLogin()

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const [tenantReady, setTenantReady] = useState(!!tokenStorage.getTenantId())

  useEffect(() => {
    if (tokenStorage.getTenantId()) {
      setTenantReady(true)
      return
    }
    void apiClient
      .get<{ id: string; name: string }[]>('/tenants')
      .then(({ data }) => {
        if (data[0]) {
          tokenStorage.setTenantId(data[0].id)
          setTenantReady(true)
        }
      })
      .catch(() => {
        setTenantReady(true) // dejar intentar igual — el backend devolverá 422
      })
  }, [])

  const onSubmit = (data: LoginFormData) => {
    void login(data)
  }

  const fillDevUser = (email: string) => {
    setValue('email', email, { shouldValidate: true })
    setValue('password', 'trace1234', { shouldValidate: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">active-trace</h1>
          <p className="mt-2 text-gray-600">Ingresá a tu cuenta</p>
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
                list="dev-users-list"
                autoComplete="email"
                {...register('email')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                aria-invalid={errors.email ? 'true' : 'false'}
              />
              {import.meta.env.DEV && (
                <datalist id="dev-users-list">
                  {DEV_USERS.map((u) => (
                    <option key={u.email} value={u.email} label={u.label} />
                  ))}
                </datalist>
              )}
              {errors.email && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                aria-invalid={errors.password ? 'true' : 'false'}
              />
              {errors.password && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors.password.message}
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
              disabled={isLoading || !tenantReady}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isLoading ? 'Ingresando…' : 'Ingresar'}
            </button>
          </form>

          {import.meta.env.DEV && (
            <div className="mt-6 border-t border-gray-100 pt-4">
              <p className="mb-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
                Acceso rápido — seed
              </p>
              <div className="flex flex-wrap gap-1.5">
                {DEV_USERS.map((u) => (
                  <button
                    key={u.email}
                    type="button"
                    onClick={() => fillDevUser(u.email)}
                    className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                  >
                    {u.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 text-center">
            <Link to="/forgot-password" className="text-sm text-indigo-600 hover:underline">
              ¿Olvidaste tu contraseña?
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
