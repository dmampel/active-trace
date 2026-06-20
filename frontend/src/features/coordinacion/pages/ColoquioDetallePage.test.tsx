import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ColoquioDetallePage } from './ColoquioDetallePage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Coord',
  roles: ['COORDINADOR'],
  permissions: ['coloquios:admin'],
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
      <MemoryRouter initialEntries={['/coordinacion/coloquios/conv1']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route
              path="/coordinacion/coloquios/:convocatoriaId"
              element={<ColoquioDetallePage />}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ColoquioDetallePage', () => {
  it('renders 3 tabs: Agenda, Reservas, Registro académico', async () => {
    server.use(
      http.get('/api/coloquios/convocatorias/:id/reservas', () => HttpResponse.json([])),
      http.get('/api/coloquios/convocatorias/:id/registro', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /agenda/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /reservas/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /registro académico/i })).toBeInTheDocument()
    })
  })

  it('shows import padron button', async () => {
    server.use(
      http.get('/api/coloquios/convocatorias/:id/reservas', () => HttpResponse.json([])),
      http.get('/api/coloquios/convocatorias/:id/registro', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /importar padrón/i })).toBeInTheDocument()
    })
  })

  it('shows empty state for registro academico when no notas', async () => {
    server.use(
      http.get('/api/coloquios/convocatorias/:id/reservas', () => HttpResponse.json([])),
      http.get('/api/coloquios/convocatorias/:id/registro', () => HttpResponse.json([])),
    )
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /registro académico/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('tab', { name: /registro académico/i }))

    await waitFor(() => {
      expect(screen.getByText(/sin notas/i)).toBeInTheDocument()
    })
  })
})
