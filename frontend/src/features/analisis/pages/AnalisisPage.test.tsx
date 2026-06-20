import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AnalisisPage } from './AnalisisPage'

const mockUser = {
  id: '1',
  email: 'prof@example.com',
  nombre: 'María',
  apellido: 'González',
  roles: ['PROFESOR'],
  permissions: ['calificaciones:importar'],
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

function renderPage(comisionId = '42') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/comision/${comisionId}/analisis`]}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/comision/:comisionId/analisis" element={<AnalisisPage />} />
            <Route path="/comision/:comisionId/importar" element={<div>Importar</div>} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function setupEmptyServer() {
  server.use(
    http.get('/api/comisiones/:id/analisis/atrasados', () => HttpResponse.json([])),
    http.get('/api/comisiones/:id/analisis/ranking', () => HttpResponse.json([])),
    http.get('/api/comisiones/:id/analisis/notas', () => HttpResponse.json([])),
    http.get('/api/comisiones/:id/analisis/reportes', () =>
      HttpResponse.json({ totalAlumnos: 0, porcentajeAlDia: 0, actividadesIncluidas: 0, promedioGeneral: 0 }),
    ),
    http.get('/api/comisiones/:id/analisis/umbral', () => HttpResponse.json({ valor: 60 })),
  )
}

function setupWithDataServer() {
  server.use(
    http.get('/api/comisiones/:id/analisis/atrasados', () =>
      HttpResponse.json([
        { id: '1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', actividadesFaltantes: 2, nota: 5 },
      ]),
    ),
    http.get('/api/comisiones/:id/analisis/ranking', () =>
      HttpResponse.json([
        { id: '1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', actividadesAprobadas: 3, nota: 5 },
      ]),
    ),
    http.get('/api/comisiones/:id/analisis/notas', () =>
      HttpResponse.json([
        { id: '1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', notaFinal: 5 },
      ]),
    ),
    http.get('/api/comisiones/:id/analisis/reportes', () =>
      HttpResponse.json({ totalAlumnos: 1, porcentajeAlDia: 0, actividadesIncluidas: 3, promedioGeneral: 5 }),
    ),
    http.get('/api/comisiones/:id/analisis/umbral', () => HttpResponse.json({ valor: 60 })),
  )
}

describe('AnalisisPage', () => {
  it('shows empty state with CTA when no data', async () => {
    setupEmptyServer()
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/aún no hay datos/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: /importar calificaciones/i })).toBeInTheDocument()
  })

  it('renders tabs when there is data', async () => {
    setupWithDataServer()
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /atrasados/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /ranking/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reportes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /notas finales/i })).toBeInTheDocument()
  })

  it('shows umbral in the header when data is loaded', async () => {
    setupWithDataServer()
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/umbral de aprobación/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/60%/)).toBeInTheDocument()
  })

  it('switches to ranking tab on click', async () => {
    setupWithDataServer()
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ranking/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /ranking/i }))
    await waitFor(() => {
      expect(screen.getByText(/García/)).toBeInTheDocument()
    })
  })
})
