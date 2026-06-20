import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AsignacionMasivaPage } from './AsignacionMasivaPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Rodríguez',
  roles: ['COORDINADOR'],
  permissions: ['equipos:admin'],
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
      <MemoryRouter initialEntries={['/equipos/masiva']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/equipos/masiva" element={<AsignacionMasivaPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AsignacionMasivaPage', () => {
  it('renders form fields', () => {
    renderPage()
    expect(screen.getByLabelText(/materia/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/cohorte/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/rol/i)).toBeInTheDocument()
  })

  it('shows validation error when submitting empty form', async () => {
    renderPage()
    const submitBtn = screen.getByRole('button', { name: /asignar/i })
    fireEvent.click(submitBtn)
    await waitFor(() => {
      expect(screen.getByText(/materia.*requerida/i)).toBeInTheDocument()
    })
  })

  it('shows per-row error detail when backend returns 400', async () => {
    server.use(
      http.post('/api/equipos/asignaciones/masiva', () =>
        HttpResponse.json(
          [
            { docenteId: 'u2', resultado: 'error', mensaje: 'Asignación duplicada' },
            { docenteId: 'u3', resultado: 'ok' },
          ],
          { status: 200 },
        ),
      ),
    )
    renderPage()

    // Fill all required fields
    fireEvent.change(screen.getByLabelText(/^materia/i), { target: { value: 'm1' } })
    fireEvent.change(screen.getByLabelText(/carrera/i), { target: { value: 'c1' } })
    fireEvent.change(screen.getByLabelText(/cohorte/i), { target: { value: 'co1' } })
    fireEvent.change(screen.getByLabelText(/rol/i), { target: { value: 'PROFESOR' } })
    fireEvent.change(screen.getByLabelText(/vigencia desde/i), { target: { value: '2024-03-01' } })

    // Add docente ids
    const docenteInput = screen.getByPlaceholderText(/id del docente/i)
    fireEvent.change(docenteInput, { target: { value: 'u2,u3' } })

    fireEvent.click(screen.getByRole('button', { name: /asignar/i }))

    await waitFor(() => {
      expect(screen.getByText(/asignación duplicada/i)).toBeInTheDocument()
    })
  })
})
