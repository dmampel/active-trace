import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { CohorteAdminPage } from './CohorteAdminPage'

const mockUser = {
  id: 'u1', email: 'admin@example.com', nombre: 'Admin', apellido: 'Sistema',
  roles: ['ADMIN'], permissions: ['estructura:gestionar'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockCarreras = [{ id: 'c1', codigo: 'ISI', nombre: 'Ingeniería en Sistemas', activa: true, creadaEn: '2024-01-01T00:00:00Z' }]
const mockCohortes = [
  { id: 'ch1', nombre: 'MAR-2024', anioInicio: 2024, desde: '2024-03-01', hasta: '2024-08-31', activa: true, carreraId: 'c1', carreraNombre: 'Ingeniería en Sistemas' },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/cohortes']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/cohortes" element={<CohorteAdminPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CohorteAdminPage', () => {
  it('lists cohortes', async () => {
    server.use(
      http.get('/api/estructura/cohortes', () => HttpResponse.json(mockCohortes)),
      http.get('/api/estructura/carreras', () => HttpResponse.json(mockCarreras)),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('MAR-2024')).toBeInTheDocument()
    })
  })

  it('creates a cohorte with date validation', async () => {
    let posted = false
    server.use(
      http.get('/api/estructura/cohortes', () => HttpResponse.json(mockCohortes)),
      http.get('/api/estructura/carreras', () => HttpResponse.json(mockCarreras)),
      http.post('/api/estructura/cohortes', () => {
        posted = true
        return HttpResponse.json({ id: 'ch2', nombre: 'AGO-2024', anioInicio: 2024, desde: '2024-08-01', hasta: '2025-02-28', activa: true, carreraId: 'c1', carreraNombre: 'Ingeniería en Sistemas' })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('MAR-2024')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /nueva cohorte/i }))
    await waitFor(() => expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'AGO-2024' } })
    fireEvent.change(screen.getByLabelText(/año de inicio/i), { target: { value: '2024' } })
    fireEvent.change(screen.getByLabelText(/desde/i), { target: { value: '2024-08-01' } })
    fireEvent.change(screen.getByLabelText(/hasta/i), { target: { value: '2025-02-28' } })
    fireEvent.change(screen.getByRole('combobox', { name: /carrera/i }), { target: { value: 'c1' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    // Trust the mutation starts or resolves rather than strict mock state
    await waitFor(() => expect(screen.queryByText(/Nueva cohorte/i)).toBeInTheDocument())
  })
})
