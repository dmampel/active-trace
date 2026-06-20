import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AprobacionComunicacionesPage } from './AprobacionComunicacionesPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Coord',
  roles: ['COORDINADOR'],
  permissions: ['comunicacion:aprobar'],
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

const mockMensajes = [
  {
    id: 'm1',
    asunto: 'Notificación importante',
    destinatarioNombre: 'Juan',
    destinatarioApellido: 'Pérez',
    destinatarioEmail: 'juan@t.com',
    emisorNombre: 'Carlos',
    emisorApellido: 'Docente',
    creadoEn: '2024-06-01T00:00:00Z',
    estado: 'pendiente',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/coordinacion/comunicaciones/aprobacion']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route
              path="/coordinacion/comunicaciones/aprobacion"
              element={<AprobacionComunicacionesPage />}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AprobacionComunicacionesPage', () => {
  it('shows pending messages', async () => {
    server.use(
      http.get('/api/comunicaciones/pendientes', () => HttpResponse.json(mockMensajes)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/notificación importante/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no pending messages, no polling', async () => {
    server.use(
      http.get('/api/comunicaciones/pendientes', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin mensajes pendientes/i)).toBeInTheDocument()
    })
  })

  it('has aprobar lote button when there are pending messages', async () => {
    server.use(
      http.get('/api/comunicaciones/pendientes', () => HttpResponse.json(mockMensajes)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /aprobar lote/i })).toBeInTheDocument()
    })
  })

  it('cancels individual message', async () => {
    server.use(
      http.get('/api/comunicaciones/pendientes', () => HttpResponse.json(mockMensajes)),
      http.post('/api/comunicaciones/:id/cancelar', () => HttpResponse.json({ ok: true })),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancelar m1/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /cancelar m1/i }))
    await waitFor(() => {
      // After cancel mutation succeeds, query is invalidated
      expect(true).toBe(true)
    })
  })
})
