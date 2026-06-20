import { createBrowserRouter, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
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

// C-23 lazy-loaded pages
const EquiposPage = lazy(() =>
  import('@/features/equipos/pages/EquiposPage').then((m) => ({ default: m.EquiposPage })),
)
const AsignacionesAdminPage = lazy(() =>
  import('@/features/equipos/pages/AsignacionesAdminPage').then((m) => ({
    default: m.AsignacionesAdminPage,
  })),
)
const AsignacionMasivaPage = lazy(() =>
  import('@/features/equipos/pages/AsignacionMasivaPage').then((m) => ({
    default: m.AsignacionMasivaPage,
  })),
)
const ClonarEquipoPage = lazy(() =>
  import('@/features/equipos/pages/ClonarEquipoPage').then((m) => ({
    default: m.ClonarEquipoPage,
  })),
)
const AvisosPage = lazy(() =>
  import('@/features/avisos/pages/AvisosPage').then((m) => ({ default: m.AvisosPage })),
)
const NuevoAvisoPage = lazy(() =>
  import('@/features/avisos/pages/NuevoAvisoPage').then((m) => ({ default: m.NuevoAvisoPage })),
)
const EditarAvisoPage = lazy(() =>
  import('@/features/avisos/pages/EditarAvisoPage').then((m) => ({
    default: m.EditarAvisoPage,
  })),
)
const ConfirmacionesAvisoPage = lazy(() =>
  import('@/features/avisos/pages/ConfirmacionesAvisoPage').then((m) => ({
    default: m.ConfirmacionesAvisoPage,
  })),
)
const MisTareasPage = lazy(() =>
  import('@/features/tareas/pages/MisTareasPage').then((m) => ({ default: m.MisTareasPage })),
)
const AdminTareasPage = lazy(() =>
  import('@/features/tareas/pages/AdminTareasPage').then((m) => ({
    default: m.AdminTareasPage,
  })),
)
const MonitorGeneralPage = lazy(() =>
  import('@/features/coordinacion/pages/MonitorGeneralPage').then((m) => ({
    default: m.MonitorGeneralPage,
  })),
)
const MonitorSeguimientoPage = lazy(() =>
  import('@/features/coordinacion/pages/MonitorSeguimientoPage').then((m) => ({
    default: m.MonitorSeguimientoPage,
  })),
)
const EncuentrosAdminPage = lazy(() =>
  import('@/features/coordinacion/pages/EncuentrosAdminPage').then((m) => ({
    default: m.EncuentrosAdminPage,
  })),
)
const ColoquiosPage = lazy(() =>
  import('@/features/coordinacion/pages/ColoquiosPage').then((m) => ({
    default: m.ColoquiosPage,
  })),
)
const ColoquioDetallePage = lazy(() =>
  import('@/features/coordinacion/pages/ColoquioDetallePage').then((m) => ({
    default: m.ColoquioDetallePage,
  })),
)
const AprobacionComunicacionesPage = lazy(() =>
  import('@/features/coordinacion/pages/AprobacionComunicacionesPage').then((m) => ({
    default: m.AprobacionComunicacionesPage,
  })),
)

function Lazy({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<div className="p-8 text-gray-400 text-sm">Cargando…</div>}>{children}</Suspense>
}

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

      // C-23 equipos routes
      {
        path: 'equipos',
        element: (
          <AuthGuard requiredPermission="equipos:ver">
            <Lazy><EquiposPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'equipos/admin',
        element: (
          <AuthGuard requiredPermission="equipos:admin">
            <Lazy><AsignacionesAdminPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'equipos/masiva',
        element: (
          <AuthGuard requiredPermission="equipos:admin">
            <Lazy><AsignacionMasivaPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'equipos/clonar',
        element: (
          <AuthGuard requiredPermission="equipos:admin">
            <Lazy><ClonarEquipoPage /></Lazy>
          </AuthGuard>
        ),
      },

      // C-23 avisos routes
      {
        path: 'avisos',
        element: (
          <AuthGuard requiredPermission="avisos:admin">
            <Lazy><AvisosPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'avisos/nuevo',
        element: (
          <AuthGuard requiredPermission="avisos:admin">
            <Lazy><NuevoAvisoPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'avisos/:id/editar',
        element: (
          <AuthGuard requiredPermission="avisos:admin">
            <Lazy><EditarAvisoPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'avisos/:id/confirmaciones',
        element: (
          <AuthGuard requiredPermission="avisos:admin">
            <Lazy><ConfirmacionesAvisoPage /></Lazy>
          </AuthGuard>
        ),
      },

      // C-23 tareas routes
      {
        path: 'tareas',
        element: (
          <AuthGuard requiredPermission="tareas:ver">
            <Lazy><MisTareasPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/tareas',
        element: (
          <AuthGuard requiredPermission="tareas:admin">
            <Lazy><AdminTareasPage /></Lazy>
          </AuthGuard>
        ),
      },

      // C-23 coordinacion routes
      {
        path: 'coordinacion/monitores',
        element: (
          <AuthGuard requiredPermission="atrasados:ver">
            <Lazy><MonitorGeneralPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/monitores/seguimiento',
        element: (
          <AuthGuard requiredPermission="atrasados:ver">
            <Lazy><MonitorSeguimientoPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/encuentros',
        element: (
          <AuthGuard requiredPermission="encuentros:ver">
            <Lazy><EncuentrosAdminPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/coloquios',
        element: (
          <AuthGuard requiredPermission="coloquios:admin">
            <Lazy><ColoquiosPage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/coloquios/:convocatoriaId',
        element: (
          <AuthGuard requiredPermission="coloquios:admin">
            <Lazy><ColoquioDetallePage /></Lazy>
          </AuthGuard>
        ),
      },
      {
        path: 'coordinacion/comunicaciones/aprobacion',
        element: (
          <AuthGuard requiredPermission="comunicacion:aprobar">
            <Lazy><AprobacionComunicacionesPage /></Lazy>
          </AuthGuard>
        ),
      },
    ],
  },

  // Fallback
  { path: '*', element: <Navigate to="/" replace /> },
])
