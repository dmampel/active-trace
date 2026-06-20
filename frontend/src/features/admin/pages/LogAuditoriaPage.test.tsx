import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { LogAuditoriaPage } from './LogAuditoriaPage'

const mockUser = {
  id: 'u1', email: 'admin@example.com', nombre: 'Admin', apellido: 'Sistema',
  roles: ['ADMIN'], permissions: ['auditoria:ver'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockLog = [
  {
    id: 'a1', fecha: '2024-06-02T10:00:00Z',
    usuarioId: 'd1', usuarioNombre: 'Carlos', usuarioApellido: 'Docente',
    accion: 'CALIFICACIONES_IMPORTAR', materia: 'Programación 4',
    filasAfectadas: 30, ip: '192.168.1.1', userAgent: 'Mozilla/5.0',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/auditoria/log']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/auditoria/log" element={<LogAuditoriaPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LogAuditoriaPage', () => {
  it('renders log entries with all columns', async () => {
    server.use(http.get('/api/auditoria/log', () => HttpResponse.json(mockLog)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('CALIFICACIONES_IMPORTAR')).toBeInTheDocument()
      expect(screen.getByText('Programación 4')).toBeInTheDocument()
      expect(screen.getByText('192.168.1.1')).toBeInTheDocument()
    })
  })

  it('filters by usuario', async () => {
    let calledWith: URLSearchParams | null = null
    server.use(http.get('/api/auditoria/log', ({ request }) => {
      calledWith = new URL(request.url).searchParams
      return HttpResponse.json(mockLog)
    }))
    renderPage()
    await waitFor(() => expect(screen.getByText('CALIFICACIONES_IMPORTAR')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/usuario/i), { target: { value: 'carlos' } })
    await waitFor(() => expect(calledWith?.get('usuario')).toBe('carlos'))
  })
})
