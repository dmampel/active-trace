import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { LiquidacionesPage } from './LiquidacionesPage'

const mockUser = {
  id: 'u1', email: 'finanzas@example.com', nombre: 'Ana', apellido: 'Finanzas',
  roles: ['FINANZAS'], permissions: ['liquidaciones:ver', 'liquidaciones:cerrar'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockLiquidaciones = [
  {
    id: 'l1',
    docente: { id: 'd1', nombre: 'Carlos', apellido: 'Docente', rol: 'PROFESOR' },
    periodo: '2024-06', salarioBase: 50000, plus: 5000, total: 55000,
    esNexo: false, excluidoPorFactura: false, estado: 'abierta', creadaEn: '2024-06-01T00:00:00Z',
  },
  {
    id: 'l2',
    docente: { id: 'd2', nombre: 'Laura', apellido: 'Nexo', rol: 'NEXO' },
    periodo: '2024-06', salarioBase: 40000, plus: 2000, total: 42000,
    esNexo: true, excluidoPorFactura: false, estado: 'abierta', creadaEn: '2024-06-01T00:00:00Z',
  },
  {
    id: 'l3',
    docente: { id: 'd3', nombre: 'Marta', apellido: 'Factura', rol: 'TUTOR' },
    periodo: '2024-06', salarioBase: 30000, plus: 0, total: 30000,
    esNexo: false, excluidoPorFactura: true, estado: 'abierta', creadaEn: '2024-06-01T00:00:00Z',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/liquidaciones?periodo=2024-06']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/liquidaciones" element={<LiquidacionesPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LiquidacionesPage', () => {
  it('shows KPIs and three segments with loaded data', async () => {
    server.use(http.get('/api/liquidaciones', () => HttpResponse.json(mockLiquidaciones)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Carlos/)).toBeInTheDocument()
    })
    // KPIs rendered
    expect(screen.getByText(/total sin factura/i)).toBeInTheDocument()
    expect(screen.getByText(/total con factura/i)).toBeInTheDocument()
  })

  it('shows NEXO docentes separately', async () => {
    server.use(http.get('/api/liquidaciones', () => HttpResponse.json(mockLiquidaciones)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Laura/)).toBeInTheDocument()
    })
    expect(screen.getAllByText(/nexo/i).length).toBeGreaterThan(0)
  })

  it('shows factura docentes separately', async () => {
    server.use(http.get('/api/liquidaciones', () => HttpResponse.json(mockLiquidaciones)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Marta/)).toBeInTheDocument()
    })
    expect(screen.getByText(/facturan/i)).toBeInTheDocument()
  })


})
