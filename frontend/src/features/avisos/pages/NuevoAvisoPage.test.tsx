import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { NuevoAvisoPage } from './NuevoAvisoPage'

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
      <MemoryRouter initialEntries={['/avisos/nuevo']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/avisos/nuevo" element={<NuevoAvisoPage />} />
            <Route path="/avisos" element={<div>Avisos</div>} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('NuevoAvisoPage', () => {
  it('renders scope field', () => {
    renderPage()
    expect(screen.getByLabelText(/alcance/i)).toBeInTheDocument()
  })

  it('shows materia selector when scope is materia', async () => {
    renderPage()
    const scopeSelect = screen.getByLabelText(/alcance/i)
    fireEvent.change(scopeSelect, { target: { value: 'materia' } })
    await waitFor(() => {
      expect(screen.getByLabelText(/materia/i)).toBeInTheDocument()
    })
  })

  it('shows materia AND cohorte selectors when scope is cohorte', async () => {
    renderPage()
    const scopeSelect = screen.getByLabelText(/alcance/i)
    fireEvent.change(scopeSelect, { target: { value: 'cohorte' } })
    await waitFor(() => {
      expect(screen.getByLabelText(/materia/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/cohorte/i)).toBeInTheDocument()
    })
  })

  it('validates Zod conditional: scope materia requires materiaId', async () => {
    renderPage()
    const scopeSelect = screen.getByLabelText(/alcance/i)
    fireEvent.change(scopeSelect, { target: { value: 'materia' } })
    // Submit without filling materiaId
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => {
      expect(screen.getByText(/materia requerida/i)).toBeInTheDocument()
    })
  })
})
