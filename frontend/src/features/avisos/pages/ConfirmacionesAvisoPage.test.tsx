import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ConfirmacionesAvisoPage } from './ConfirmacionesAvisoPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Rodríguez',
  roles: ['COORDINADOR'],
  permissions: ['avisos:admin'],
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
      <MemoryRouter initialEntries={['/avisos/av1/confirmaciones']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/avisos/:id/confirmaciones" element={<ConfirmacionesAvisoPage />} />
            <Route path="/avisos" element={<div>Avisos</div>} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ConfirmacionesAvisoPage', () => {
  it('shows list of users who confirmed', async () => {
    server.use(
      http.get('/api/avisos/:id', () =>
        HttpResponse.json({
          id: 'av1',
          titulo: 'Aviso con ACK',
          requireAck: true,
          activo: true,
          scope: 'global',
          roles: ['PROFESOR'],
          severidad: 'info',
          cuerpo: '',
          vigenciaDesde: '2024-01-01',
          vigenciaHasta: null,
          orden: 0,
          creadoPor: 'u1',
          creadoEn: '2024-01-01T00:00:00Z',
        }),
      ),
      http.get('/api/avisos/:id/confirmaciones', () =>
        HttpResponse.json([
          {
            id: 'c1',
            avisoId: 'av1',
            userId: 'u2',
            userNombre: 'Juan',
            userApellido: 'Pérez',
            userEmail: 'juan@t.com',
            confirmedAt: '2024-06-01T10:00:00Z',
          },
        ]),
      ),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText(/juan/i).length).toBeGreaterThan(0)
    })
  })

  it('shows empty state when nobody confirmed yet', async () => {
    server.use(
      http.get('/api/avisos/:id', () =>
        HttpResponse.json({
          id: 'av1',
          titulo: 'Aviso sin confirmaciones',
          requireAck: true,
          activo: true,
          scope: 'global',
          roles: ['PROFESOR'],
          severidad: 'info',
          cuerpo: '',
          vigenciaDesde: '2024-01-01',
          vigenciaHasta: null,
          orden: 0,
          creadoPor: 'u1',
          creadoEn: '2024-01-01T00:00:00Z',
        }),
      ),
      http.get('/api/avisos/:id/confirmaciones', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/nadie confirmó/i)).toBeInTheDocument()
    })
  })
})
