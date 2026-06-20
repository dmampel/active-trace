import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AsignacionesAdminPage } from './AsignacionesAdminPage'

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

const mockAsignaciones = [
  {
    id: 'a1',
    docenteId: 'u2',
    docenteNombre: 'Carlos',
    docenteApellido: 'López',
    materiaId: 'm1',
    materiaNombre: 'Matemática',
    carreraId: 'c1',
    carreraNombre: 'Ingeniería',
    cohorteId: 'co1',
    cohorteNombre: '2024',
    rol: 'PROFESOR',
    vigenciaDesde: '2024-03-01',
    vigenciaHasta: null,
    estado: 'activa',
  },
  {
    id: 'a2',
    docenteId: 'u3',
    docenteNombre: 'Ana',
    docenteApellido: 'García',
    materiaId: 'm2',
    materiaNombre: 'Física',
    carreraId: 'c1',
    carreraNombre: 'Ingeniería',
    cohorteId: 'co1',
    cohorteNombre: '2024',
    rol: 'TUTOR',
    vigenciaDesde: '2024-03-01',
    vigenciaHasta: null,
    estado: 'activa',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/equipos']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/equipos" element={<AsignacionesAdminPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AsignacionesAdminPage', () => {
  it('shows all asignaciones', async () => {
    server.use(
      http.get('/api/equipos/asignaciones', () => HttpResponse.json(mockAsignaciones)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/carlos/i)).toBeInTheDocument()
      expect(screen.getByText(/ana/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no asignaciones', async () => {
    server.use(
      http.get('/api/equipos/asignaciones', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin asignaciones/i)).toBeInTheDocument()
    })
  })

  it('has filter inputs for materia and rol', async () => {
    server.use(
      http.get('/api/equipos/asignaciones', () => HttpResponse.json(mockAsignaciones)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/materia/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/rol/i)).toBeInTheDocument()
    })
  })

  it('clears filters when clear button is clicked', async () => {
    server.use(
      http.get('/api/equipos/asignaciones', () => HttpResponse.json(mockAsignaciones)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/materia/i)).toBeInTheDocument()
    })
    const materiaInput = screen.getByPlaceholderText(/materia/i)
    fireEvent.change(materiaInput, { target: { value: 'Matemática' } })
    const clearBtn = screen.getByRole('button', { name: /limpiar/i })
    fireEvent.click(clearBtn)
    expect((materiaInput as HTMLInputElement).value).toBe('')
  })

  it('has export button', async () => {
    server.use(
      http.get('/api/equipos/asignaciones', () => HttpResponse.json(mockAsignaciones)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /exportar/i })).toBeInTheDocument()
    })
  })
})
