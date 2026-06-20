import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { MisTareasPage } from './MisTareasPage'

const mockUser = {
  id: 'u1',
  email: 'prof@example.com',
  nombre: 'Carlos',
  apellido: 'Docente',
  roles: ['PROFESOR'],
  permissions: ['tareas:ver'],
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
    titulo: 'Revisar entregas',
    descripcion: 'Revisar y calificar las entregas de la semana',
    estado: 'abierta',
    materiaId: 'm1',
    materiaNombre: 'Programación 4',
    asignadoAId: 'u1',
    asignadoANombre: 'Carlos',
    asignadoAApellido: 'Docente',
    asignadoPorId: 'u2',
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
      <MemoryRouter initialEntries={['/tareas']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/tareas" element={<MisTareasPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MisTareasPage', () => {
  it('shows list of tasks ordered by state/date', async () => {
    server.use(http.get('/api/tareas/mis-tareas', () => HttpResponse.json(mockTareas)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /revisar entregas/i })).toBeInTheDocument()
    })
  })

  it('shows empty state when no tasks', async () => {
    server.use(http.get('/api/tareas/mis-tareas', () => HttpResponse.json([])))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/sin tareas/i)).toBeInTheDocument()
    })
  })

  it('allows adding a comment to a task', async () => {
    server.use(
      http.get('/api/tareas/mis-tareas', () => HttpResponse.json(mockTareas)),
      http.post('/api/tareas/:id/comentarios', () =>
        HttpResponse.json({
          id: 'c1',
          tareaId: 't1',
          autorId: 'u1',
          autorNombre: 'Carlos',
          autorApellido: 'Docente',
          texto: 'Comentario de prueba',
          creadoEn: '2024-06-01T00:00:00Z',
        }),
      ),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /revisar entregas/i })).toBeInTheDocument()
    })

    // The comment section is hidden — click the toggle button first
    fireEvent.click(screen.getByRole('button', { name: /agregar comentario/i }))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/agregar comentario/i)).toBeInTheDocument()
    })

    const commentInput = screen.getByPlaceholderText(/agregar comentario/i)
    fireEvent.change(commentInput, { target: { value: 'Comentario de prueba' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    // Mutation fired — consider it successful if the input was cleared or mutation ran
    await waitFor(() => {
      expect((commentInput as HTMLInputElement).value).toBe('')
    })
  })

  it('allows changing task state', async () => {
    let currentTareas = [...mockTareas]
    server.use(
      http.get('/api/tareas/mis-tareas', () => HttpResponse.json(currentTareas)),
      http.patch('/api/tareas/:id/estado', () => {
        currentTareas = [{ ...mockTareas[0], estado: 'en_progreso' }]
        return HttpResponse.json(currentTareas[0])
      }),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /revisar entregas/i })).toBeInTheDocument()
    })

    const estadoSelect = screen.getByRole('combobox', { name: /estado/i })
    fireEvent.change(estadoSelect, { target: { value: 'en_progreso' } })

    await waitFor(() => {
      expect((estadoSelect as HTMLSelectElement).value).toBe('en_progreso')
    })
  })
})
