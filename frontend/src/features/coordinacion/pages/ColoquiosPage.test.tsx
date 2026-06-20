import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ColoquiosPage } from './ColoquiosPage'

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

const mockMetricas = {
  totalAlumnosCargados: 120,
  instanciasActivas: 3,
  reservasActivas: 45,
  notasRegistradas: 30,
}

const mockConvocatorias = [
  {
    id: 'conv1',
    materiaId: 'm1',
    materiaNombre: 'Programación 4',
    instanciaNombre: 'Primer período 2024',
    diasDisponibles: ['Lunes', 'Miércoles'],
    cuposPorDia: 10,
    totalAlumnosConvocados: 25,
    reservasActivas: 18,
    notasRegistradas: 0,
    activa: true,
    creadaEn: '2024-01-01T00:00:00Z',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/coordinacion/coloquios']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/coordinacion/coloquios" element={<ColoquiosPage />} />
            <Route
              path="/coordinacion/coloquios/:convocatoriaId"
              element={<div>Detalle Coloquio</div>}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ColoquiosPage', () => {
  it('shows KPI header metrics', async () => {
    server.use(
      http.get('/api/coloquios/metricas', () => HttpResponse.json(mockMetricas)),
      http.get('/api/coloquios/convocatorias', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  it('lists convocatorias with metrics', async () => {
    server.use(
      http.get('/api/coloquios/metricas', () => HttpResponse.json(mockMetricas)),
      http.get('/api/coloquios/convocatorias', () => HttpResponse.json(mockConvocatorias)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/programación 4/i)).toBeInTheDocument()
      expect(screen.getByText(/primer período/i)).toBeInTheDocument()
    })
  })

  it('shows button to create new convocatoria', async () => {
    server.use(
      http.get('/api/coloquios/metricas', () => HttpResponse.json(mockMetricas)),
      http.get('/api/coloquios/convocatorias', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /nueva convocatoria/i })).toBeInTheDocument()
    })
  })
})
