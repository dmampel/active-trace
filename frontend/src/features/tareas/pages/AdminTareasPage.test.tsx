import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { AdminTareasPage } from './AdminTareasPage'

const mockUser = {
  id: 'u1',
  email: 'coord@example.com',
  nombre: 'Laura',
  apellido: 'Coord',
  roles: ['COORDINADOR'],
  permissions: ['tareas:admin'],
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

const mockTareas = [
  {
    id: 't1',
    titulo: 'Tarea abierta',
    descripcion: '',
    estado: 'abierta',
    materiaId: 'm1',
    materiaNombre: 'Programación 4',
    asignadoAId: 'u2',
    asignadoANombre: 'Carlos',
    asignadoAApellido: 'Docente',
    asignadoPorId: 'u1',
    asignadoPorNombre: 'Laura',
    asignadoPorApellido: 'Coord',
    comentarios: [],
    creadaEn: '2024-01-01T00:00:00Z',
    actualizadaEn: '2024-01-01T00:00:00Z',
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/coordinacion/tareas']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/coordinacion/tareas" element={<AdminTareasPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminTareasPage', () => {
  it('shows all tenant tasks', async () => {
    server.use(http.get('/api/tareas', () => HttpResponse.json(mockTareas)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/tarea abierta/i)).toBeInTheDocument()
    })
  })

  it('has filters for estado and docente', async () => {
    server.use(http.get('/api/tareas', () => HttpResponse.json(mockTareas)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText(/estado/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/docente/i)).toBeInTheDocument()
    })
  })

  it('clears filters when clear button clicked', async () => {
    server.use(http.get('/api/tareas', () => HttpResponse.json(mockTareas)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/docente/i)).toBeInTheDocument()
    })
    const docenteInput = screen.getByPlaceholderText(/docente/i)
    fireEvent.change(docenteInput, { target: { value: 'Carlos' } })
    fireEvent.click(screen.getByRole('button', { name: /limpiar/i }))
    expect((docenteInput as HTMLInputElement).value).toBe('')
  })

  it('allows coordinador to change task state', async () => {
    server.use(
      http.get('/api/tareas', () => HttpResponse.json(mockTareas)),
      http.patch('/api/tareas/:id/estado', () =>
        HttpResponse.json({ ...mockTareas[0], estado: 'completada' }),
      ),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/tarea abierta/i)).toBeInTheDocument()
    })
    const estadoSelect = screen.getAllByRole('combobox')[0]
    fireEvent.change(estadoSelect, { target: { value: 'completada' } })
    await waitFor(() => {
      expect((estadoSelect as HTMLSelectElement).value).toBe('completada')
    })
  })
})
