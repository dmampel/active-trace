import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { EncuentrosAdminPage } from './EncuentrosAdminPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Coord',
  roles: ['COORDINADOR'],
  permissions: ['encuentros:ver'],
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

const mockEncuentros = [
  {
    id: 'e1',
    materiaId: 'm1',
    materiaNombre: 'Programación 4',
    docenteId: 'u2',
    docenteNombre: 'Carlos',
    docenteApellido: 'Docente',
    fecha: '2024-06-01',
    horaInicio: '18:00',
    horaFin: '20:00',
    estado: 'realizado',
    grabacionUrl: null,
    descripcion: '',
  },
]

const mockGuardias = [
  {
    id: 'g1',
    tutorId: 'u3',
    tutorNombre: 'Ana',
    tutorApellido: 'Tutora',
    materiaId: 'm1',
    materiaNombre: 'Programación 4',
    carreraId: 'c1',
    carreraNombre: 'Ingeniería',
    cohorteId: 'co1',
    cohorteNombre: '2024',
    dia: '2024-06-01',
    horario: '14:00-16:00',
    estado: 'cubierta',
    comentarios: '',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/coordinacion/encuentros']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/coordinacion/encuentros" element={<EncuentrosAdminPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EncuentrosAdminPage', () => {
  it('lists all tenant encuentros', async () => {
    server.use(
      http.get('/api/encuentros', () => HttpResponse.json(mockEncuentros)),
      http.get('/api/guardias', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/programación 4/i)).toBeInTheDocument()
    })
  })

  it('has filters for materia, docente, estado', async () => {
    server.use(
      http.get('/api/encuentros', () => HttpResponse.json([])),
      http.get('/api/guardias', () => HttpResponse.json([])),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/materia/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/docente/i)).toBeInTheDocument()
    })
  })

  it('shows guardias section with export button', async () => {
    server.use(
      http.get('/api/encuentros', () => HttpResponse.json([])),
      http.get('/api/guardias', () => HttpResponse.json(mockGuardias)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /guardias/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /exportar guardias/i })).toBeInTheDocument()
    })
  })
})
