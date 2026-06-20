import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { UsuariosAdminPage } from './UsuariosAdminPage'

const mockUser = {
  id: 'u1', email: 'admin@example.com', nombre: 'Admin', apellido: 'Sistema',
  roles: ['ADMIN'], permissions: ['usuarios:gestionar'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockUsuarios = [
  {
    id: 'u2', nombre: 'Carlos', apellido: 'Docente', email: 'carlos@example.com',
    roles: ['PROFESOR'], activo: true, modalidadCobro: 'liquidacion', regional: 'NOA',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/usuarios']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/usuarios" element={<UsuariosAdminPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('UsuariosAdminPage', () => {
  it('lists usuarios', async () => {
    server.use(http.get('/api/admin/usuarios', () => HttpResponse.json(mockUsuarios)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Carlos/)).toBeInTheDocument()
      expect(screen.getByText('carlos@example.com')).toBeInTheDocument()
    })
  })

  it('creates a user', async () => {
    let posted = false
    server.use(
      http.get('/api/admin/usuarios', () => HttpResponse.json(mockUsuarios)),
      http.post('/api/admin/usuarios', () => {
        posted = true
        return HttpResponse.json({ id: 'u3', nombre: 'Laura', apellido: 'Nueva', email: 'laura@example.com', roles: ['TUTOR'], activo: true, modalidadCobro: 'liquidacion', regional: null })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/Carlos/)).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /nuevo usuario/i }))
    await waitFor(() => expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Laura' } })
    fireEvent.change(screen.getByLabelText(/apellido/i), { target: { value: 'Nueva' } })
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'laura@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(posted).toBe(true))
  })

  it('deactivates a user', async () => {
    let patched = false
    server.use(
      http.get('/api/admin/usuarios', () => HttpResponse.json(mockUsuarios)),
      http.patch('/api/admin/usuarios/:id', () => {
        patched = true
        return HttpResponse.json({ ...mockUsuarios[0], activo: false })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/Carlos/)).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /desactivar/i }))
    await waitFor(() => expect(patched).toBe(true))
  })
})
