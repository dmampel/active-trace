import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AuthGuard } from '@/features/auth/components/AuthGuard'
import { AppLayout } from '@/shared/components/AppLayout'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { TwoFactorPage } from '@/features/auth/pages/TwoFactorPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/pages/ResetPasswordPage'
import { DashboardPage } from '@/app/pages/DashboardPage'
import { ImportarCalificacionesPage } from '@/features/importacion/pages/ImportarCalificacionesPage'
import { AnalisisPage } from '@/features/analisis/pages/AnalisisPage'
import { ComunicacionPage } from '@/features/comunicacion/pages/ComunicacionPage'
import { MonitorDocentePage } from '@/features/analisis/pages/MonitorDocentePage'

export const router = createBrowserRouter([
  // Public routes
  { path: '/login', element: <LoginPage /> },
  { path: '/login/2fa', element: <TwoFactorPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },

  // Protected routes wrapped in AuthGuard → AppLayout
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      // C-22 comisión routes
      {
        path: 'comision/:comisionId/importar',
        element: (
          <AuthGuard requiredPermission="calificaciones:importar">
            <ImportarCalificacionesPage />
          </AuthGuard>
        ),
      },
      { path: 'comision/:comisionId/analisis', element: <AnalisisPage /> },
      { path: 'comision/:comisionId/comunicacion', element: <ComunicacionPage /> },
      { path: 'comision/:comisionId/monitor', element: <MonitorDocentePage /> },
    ],
  },

  // Fallback
  { path: '*', element: <Navigate to="/" replace /> },
])
