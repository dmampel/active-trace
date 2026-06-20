import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AuditoriaPage } from './AuditoriaPage'

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

const mockPanel = {
  accionesPorDia: [
    { fecha: '2024-06-01', total: 15 },
    { fecha: '2024-06-02', total: 42 },
  ],
  estadoComunicaciones: [
    {
      docenteId: 'd1', docenteNombre: 'Carlos', docenteApellido: 'Docente',
      pendiente: 2, enviando: 0, enviado: 10, fallido: 1, cancelado: 0,
    },
  ],
  ultimasAcciones: [
    {
      id: 'a1', fecha: '2024-06-02T10:00:00Z',
      usuarioId: 'd1', usuarioNombre: 'Carlos', usuarioApellido: 'Docente',
      accion: 'CALIFICACIONES_IMPORTAR', materia: 'Programación 4',
      filasAfectadas: 30, ip: '192.168.1.1', userAgent: null,
    },
  ],
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/auditoria']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/admin/auditoria" element={<AuditoriaPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AuditoriaPage', () => {
  it('shows panel with acciones por dia, estado comms y ultimas acciones', async () => {
    server.use(http.get('/api/auditoria/panel', () => HttpResponse.json(mockPanel)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('CALIFICACIONES_IMPORTAR')).toBeInTheDocument()
    })
    expect(screen.getByText('2024-06-01')).toBeInTheDocument()
    expect(screen.getAllByText(/Carlos/)[0]).toBeInTheDocument()
  })

  it('applies date filter', async () => {
    let calledWith: URLSearchParams | null = null
    server.use(http.get('/api/auditoria/panel', ({ request }) => {
      calledWith = new URL(request.url).searchParams
      return HttpResponse.json(mockPanel)
    }))
    renderPage()
    await waitFor(() => expect(screen.getByText('CALIFICACIONES_IMPORTAR')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/desde/i), { target: { value: '2024-06-01' } })
    await waitFor(() => expect(calledWith?.get('desde')).toBe('2024-06-01'))
  })
})
