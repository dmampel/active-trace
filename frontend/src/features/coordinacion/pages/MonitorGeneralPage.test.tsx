import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { MonitorGeneralPage } from './MonitorGeneralPage'

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

const mockAlumnos = [
  {
    alumnoId: 'a1',
    alumnoNombre: 'Juan',
    alumnoApellido: 'Pérez',
    email: 'juan@t.com',
    materia: 'Programación 4',
    comision: '1A',
    regional: 'Buenos Aires',
    estado: 'Atrasado',
    actividadesCumplidas: 2,
    actividadesTotales: 5,
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/coordinacion/monitores']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/coordinacion/monitores" element={<MonitorGeneralPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MonitorGeneralPage', () => {
  it('shows alumnos in monitor', async () => {
    server.use(http.get('/api/monitor', () => HttpResponse.json(mockAlumnos)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/juan/i)).toBeInTheDocument()
    })
  })

  it('has filter inputs for materia, regional, comision, estado', async () => {
    server.use(http.get('/api/monitor', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/materia/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/regional/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/comisión/i)).toBeInTheDocument()
    })
  })

  it('has export button', async () => {
    server.use(http.get('/api/monitor', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /exportar/i })).toBeInTheDocument()
    })
  })

  it('clears filters on clear button click', async () => {
    server.use(http.get('/api/monitor', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/materia/i)).toBeInTheDocument()
    })
    const materiaInput = screen.getByPlaceholderText(/materia/i)
    fireEvent.change(materiaInput, { target: { value: 'Prog 4' } })
    fireEvent.click(screen.getByRole('button', { name: /limpiar/i }))
    expect((materiaInput as HTMLInputElement).value).toBe('')
  })
})
