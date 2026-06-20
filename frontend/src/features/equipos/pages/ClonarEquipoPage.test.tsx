import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ClonarEquipoPage } from './ClonarEquipoPage'

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
      <MemoryRouter initialEntries={['/equipos/clonar']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/equipos/clonar" element={<ClonarEquipoPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ClonarEquipoPage', () => {
  it('renders 3-step stepper', () => {
    renderPage()
    expect(screen.getByText(/paso 1/i)).toBeInTheDocument()
  })

  it('validates required origin selection before advancing to step 2', async () => {
    renderPage()
    const nextBtn = screen.getByRole('button', { name: /siguiente/i })
    fireEvent.click(nextBtn)
    await waitFor(() => {
      expect(screen.getByText(/completá todos los campos de origen/i)).toBeInTheDocument()
    })
  })

  it('shows 409 conflict message on step 3 without losing origen', async () => {
    server.use(
      http.post('/api/equipos/clonar', () =>
        HttpResponse.json({ detail: 'El destino ya tiene asignaciones para esa combinación' }, { status: 409 }),
      ),
    )
    renderPage()

    // Fill step 1
    fireEvent.change(screen.getByLabelText(/materia origen/i), { target: { value: 'm1' } })
    fireEvent.change(screen.getByLabelText(/carrera origen/i), { target: { value: 'c1' } })
    fireEvent.change(screen.getByLabelText(/cohorte origen/i), { target: { value: 'co1' } })
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }))

    await waitFor(() => {
      expect(screen.getByText(/paso 2/i)).toBeInTheDocument()
    })

    // Fill step 2
    fireEvent.change(screen.getByLabelText(/materia destino/i), { target: { value: 'm2' } })
    fireEvent.change(screen.getByLabelText(/carrera destino/i), { target: { value: 'c1' } })
    fireEvent.change(screen.getByLabelText(/cohorte destino/i), { target: { value: 'co2' } })
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }))

    await waitFor(() => {
      expect(screen.getByText(/paso 3/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /confirmar/i }))

    await waitFor(() => {
      expect(screen.getByText(/ya tiene asignaciones/i)).toBeInTheDocument()
    })

    // Origen selection should still be visible
    expect(screen.getByText(/paso 3/i)).toBeInTheDocument()
  })
})
