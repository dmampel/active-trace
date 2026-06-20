import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { EquiposPage } from './EquiposPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Rodríguez',
  roles: ['COORDINADOR'],
  permissions: ['equipos:ver', 'equipos:admin'],
}

function makeCtx(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: mockUser,
    session: null,
    isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined,
    clearSession: () => undefined,
    ...overrides,
  }
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/equipos']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/equipos" element={<EquiposPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EquiposPage', () => {
  it('shows empty state when no equipos', async () => {
    server.use(
      http.get('/api/equipos/mis-equipos', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin asignaciones/i)).toBeInTheDocument()
    })
  })

  it('renders tabs: Mis asignaciones, Actividad, Comunicaciones', async () => {
    server.use(
      http.get('/api/equipos/mis-equipos', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /mis asignaciones/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /actividad/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /comunicaciones/i })).toBeInTheDocument()
    })
  })

  it('shows equipo data when loaded', async () => {
    server.use(
      http.get('/api/equipos/mis-equipos', () =>
        HttpResponse.json([
          {
            id: 'e1',
            materiaId: 'm1',
            materiaNombre: 'Programación 4',
            carreraId: 'c1',
            carreraNombre: 'Ingeniería',
            cohorteId: 'co1',
            cohorteNombre: '2024',
            asignaciones: [
              {
                id: 'a1',
                docenteId: 'u1',
                docenteNombre: 'Laura',
                docenteApellido: 'Rodríguez',
                materiaId: 'm1',
                materiaNombre: 'Programación 4',
                carreraId: 'c1',
                carreraNombre: 'Ingeniería',
                cohorteId: 'co1',
                cohorteNombre: '2024',
                rol: 'COORDINADOR',
                vigenciaDesde: '2024-03-01',
                vigenciaHasta: null,
                estado: 'activa',
              },
            ],
          },
        ]),
      ),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/programación 4/i)).toBeInTheDocument()
    })
  })

  it('switches to Actividad tab on click', async () => {
    server.use(
      http.get('/api/equipos/mis-equipos', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /actividad/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('tab', { name: /actividad/i }))
    // Tab panel for actividad should be visible
    expect(screen.getByRole('tab', { name: /actividad/i })).toHaveAttribute('aria-selected', 'true')
  })
})
