import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { MonitorSeguimientoPage } from './MonitorSeguimientoPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Coord',
  roles: ['COORDINADOR'],
  permissions: ['atrasados:ver'],
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
      <MemoryRouter initialEntries={['/coordinacion/monitores/seguimiento']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/coordinacion/monitores/seguimiento" element={<MonitorSeguimientoPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MonitorSeguimientoPage', () => {
  it('shows date range pickers', async () => {
    server.use(http.get('/api/monitor/seguimiento', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/fecha desde/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/fecha hasta/i)).toBeInTheDocument()
    })
  })

  it('works without date range (empty dates)', async () => {
    server.use(http.get('/api/monitor/seguimiento', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin resultados/i)).toBeInTheDocument()
    })
  })

  it('filters by date range when dates provided', async () => {
    server.use(http.get('/api/monitor/seguimiento', () =>
      HttpResponse.json([
        {
          alumnoId: 'a1',
          alumnoNombre: 'Juan',
          alumnoApellido: 'Pérez',
          email: 'juan@t.com',
          materia: 'Programación 4',
          comision: '1A',
          regional: 'Buenos Aires',
          estado: 'Al día',
          actividadesCumplidas: 5,
          actividadesTotales: 5,
        },
      ]),
    ))
    renderPage()
    fireEvent.change(screen.getByLabelText(/fecha desde/i), {
      target: { value: '2024-01-01' },
    })
    fireEvent.change(screen.getByLabelText(/fecha hasta/i), {
      target: { value: '2024-06-30' },
    })
    fireEvent.click(screen.getByRole('button', { name: /buscar/i }))
    await waitFor(() => {
      expect(screen.getByText(/juan/i)).toBeInTheDocument()
    })
  })
})
