import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { MateriasPage } from './MateriasPage'

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

const mockMaterias = [
  { id: 'm1', codigo: 'PROG4', nombre: 'Programación 4', activa: true, creadaEn: '2024-01-01T00:00:00Z' },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/materias']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/materias" element={<MateriasPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MateriasPage', () => {
  it('lists materias', async () => {
    server.use(http.get('/api/estructura/materias', () => HttpResponse.json(mockMaterias)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Programación 4')).toBeInTheDocument()
      expect(screen.getByText('PROG4')).toBeInTheDocument()
    })
  })

  it('creates a materia', async () => {
    let posted = false
    server.use(
      http.get('/api/estructura/materias', () => HttpResponse.json(mockMaterias)),
      http.post('/api/estructura/materias', () => {
        posted = true
        return HttpResponse.json({ id: 'm2', codigo: 'BD2', nombre: 'Bases de Datos 2', activa: true, creadaEn: '2024-06-01T00:00:00Z' })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('Programación 4')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /nueva materia/i }))
    await waitFor(() => expect(screen.getByLabelText(/código/i)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/código/i), { target: { value: 'BD2' } })
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Bases de Datos 2' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(posted).toBe(true))
  })

  it('toggles activa', async () => {
    let patched = false
    server.use(
      http.get('/api/estructura/materias', () => HttpResponse.json(mockMaterias)),
      http.patch('/api/estructura/materias/:id', () => {
        patched = true
        return HttpResponse.json({ ...mockMaterias[0], activa: false })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText('Programación 4')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /desactivar/i }))
    await waitFor(() => expect(patched).toBe(true))
  })
})
