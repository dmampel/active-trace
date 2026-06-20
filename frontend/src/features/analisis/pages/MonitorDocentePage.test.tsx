import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { MonitorDocentePage } from './MonitorDocentePage'

const mockUser = {
  id: 'prof-1',
  email: 'prof@example.com',
  nombre: 'María',
  apellido: 'González',
  roles: ['PROFESOR'],
  permissions: ['comisiones:read'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser,
    session: null,
    isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined,
    clearSession: () => undefined,
  }
}

const mockAlumnos = [
  {
    id: '1',
    nombre: 'Ana',
    apellido: 'García',
    email: 'ana@t.com',
    comision: 'COM-A',
    regional: 'UTN BA',
    actividad: 'TP1',
    actividadesCumplidas: 5,
  },
  {
    id: '2',
    nombre: 'Luis',
    apellido: 'Pérez',
    email: 'luis@t.com',
    comision: 'COM-B',
    regional: 'UTN Córdoba',
    actividad: 'TP2',
    actividadesCumplidas: 2,
  },
]

function renderPage(comisionId = '42') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/comision/${comisionId}/monitor`]}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/comision/:comisionId/monitor" element={<MonitorDocentePage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MonitorDocentePage', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/comisiones/:id/monitor', () => HttpResponse.json(mockAlumnos)),
    )
  })

  it('renders alumnos returned by the API', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/García/)).toBeInTheDocument()
    })
    expect(screen.getByText(/Pérez/)).toBeInTheDocument()
  })

  it('updates filtros state when typing in alumno filter', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())

    server.use(
      http.get('/api/comisiones/:id/monitor', ({ request }) => {
        const url = new URL(request.url)
        const alumno = url.searchParams.get('alumno')
        return HttpResponse.json(alumno ? mockAlumnos.filter((a) => a.nombre.toLowerCase().includes(alumno)) : mockAlumnos)
      }),
    )

    const input = screen.getByRole('textbox', { name: /filtrar por alumno/i })
    fireEvent.change(input, { target: { value: 'ana' } })
    // The hook will refetch — just verify no crash
    expect(input).toHaveValue('ana')
  })

  it('shows Limpiar filtros button when any filter is active', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())

    const input = screen.getByRole('textbox', { name: /filtrar por alumno/i })
    fireEvent.change(input, { target: { value: 'test' } })
    expect(screen.getByRole('button', { name: /limpiar filtros/i })).toBeInTheDocument()
  })

  it('clears all filters when Limpiar filtros is clicked', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())

    const input = screen.getByRole('textbox', { name: /filtrar por alumno/i })
    fireEvent.change(input, { target: { value: 'test' } })

    const limpiarBtn = screen.getByRole('button', { name: /limpiar filtros/i })
    fireEvent.click(limpiarBtn)
    expect(input).toHaveValue('')
    expect(screen.queryByRole('button', { name: /limpiar filtros/i })).not.toBeInTheDocument()
  })
})
