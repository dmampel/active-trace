import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { CarrerasPage } from './CarrerasPage'

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

const mockCarreras = [
  { id: 'c1', codigo: 'ISI', nombre: 'Ingeniería en Sistemas', activa: true, creadaEn: '2024-01-01T00:00:00Z' },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/carreras']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/carreras" element={<CarrerasPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CarrerasPage', () => {
  it('lists carreras', async () => {
    server.use(http.get('/api/estructura/carreras', () => HttpResponse.json(mockCarreras)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Ingeniería en Sistemas')).toBeInTheDocument()
      expect(screen.getByText('ISI')).toBeInTheDocument()
    })
  })

  it('creates a carrera', async () => {
    let posted = false
    server.use(
      http.get('/api/estructura/carreras', () => HttpResponse.json(mockCarreras)),
      http.post('/api/estructura/carreras', () => {
        posted = true
        return HttpResponse.json({ id: 'c2', codigo: 'TUP', nombre: 'Tecnicatura UP', activa: true, creadaEn: '2024-06-01T00:00:00Z' })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('Ingeniería en Sistemas')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /nueva carrera/i }))
    await waitFor(() => expect(screen.getByLabelText(/código/i)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/código/i), { target: { value: 'TUP' } })
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Tecnicatura UP' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(posted).toBe(true))
  })

  it('toggles activa status', async () => {
    let patched = false
    server.use(
      http.get('/api/estructura/carreras', () => HttpResponse.json(mockCarreras)),
      http.patch('/api/estructura/carreras/:id', () => {
        patched = true
        return HttpResponse.json({ ...mockCarreras[0], activa: false })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('Ingeniería en Sistemas')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /desactivar/i }))
    await waitFor(() => expect(patched).toBe(true))
  })
})
