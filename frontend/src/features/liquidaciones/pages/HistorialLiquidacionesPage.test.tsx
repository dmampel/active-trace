import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { HistorialLiquidacionesPage } from './HistorialLiquidacionesPage'

const mockUser = {
  id: 'u1', email: 'finanzas@example.com', nombre: 'Ana', apellido: 'Finanzas',
  roles: ['FINANZAS'], permissions: ['liquidaciones:ver'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockHistorial = [
  {
    id: 'l1',
    docente: { id: 'd1', nombre: 'Carlos', apellido: 'Docente', rol: 'PROFESOR' },
    periodo: '2024-05', salarioBase: 50000, plus: 5000, total: 55000,
    esNexo: false, excluidoPorFactura: false, estado: 'cerrada', creadaEn: '2024-05-01T00:00:00Z',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/liquidaciones/historial']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/liquidaciones/historial" element={<HistorialLiquidacionesPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HistorialLiquidacionesPage', () => {
  it('shows closed liquidaciones and no cerrar button', async () => {
    server.use(http.get('/api/liquidaciones/historial', () => HttpResponse.json(mockHistorial)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Carlos/)).toBeInTheDocument()
      expect(screen.getByText('2024-05')).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /cerrar/i })).not.toBeInTheDocument()
  })

  it('shows empty state when no historial', async () => {
    server.use(http.get('/api/liquidaciones/historial', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin historial/i)).toBeInTheDocument()
    })
  })
})
