import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AvisosPage } from './AvisosPage'

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
      <MemoryRouter initialEntries={['/avisos']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/avisos" element={<AvisosPage />} />
            <Route path="/avisos/nuevo" element={<div>Nuevo Aviso</div>} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const mockAvisos = [
  {
    id: 'av1',
    scope: 'global',
    roles: ['PROFESOR'],
    severidad: 'info',
    titulo: 'Aviso activo',
    cuerpo: 'Contenido del aviso',
    vigenciaDesde: '2024-01-01',
    vigenciaHasta: '2099-12-31',
    orden: 0,
    requireAck: false,
    activo: true,
    creadoPor: 'u1',
    creadoEn: '2024-01-01T00:00:00Z',
  },
]

describe('AvisosPage', () => {
  it('shows active avisos', async () => {
    server.use(
      http.get('/api/avisos', () => HttpResponse.json(mockAvisos)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/aviso activo/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no avisos', async () => {
    server.use(
      http.get('/api/avisos', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin avisos/i)).toBeInTheDocument()
    })
  })

  it('has button to create new aviso', async () => {
    server.use(
      http.get('/api/avisos', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /nuevo aviso/i })).toBeInTheDocument()
    })
  })
})
