import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ComunicacionPage } from './ComunicacionPage'

const mockUser = {
  id: '1',
  email: 'prof@example.com',
  nombre: 'María',
  apellido: 'González',
  roles: ['PROFESOR'],
  permissions: ['comunicacion:read'],
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

const mockAtrasados = [
  {
    id: 'al-1',
    nombre: 'Ana',
    apellido: 'García',
    email: 'ana@t.com',
    actividadesFaltantes: 2,
    nota: 5,
  },
  {
    id: 'al-2',
    nombre: 'Luis',
    apellido: 'Pérez',
    email: 'luis@t.com',
    actividadesFaltantes: 1,
    nota: 7,
  },
]

function renderPage(comisionId = '42') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/comision/${comisionId}/comunicacion`]}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/comision/:comisionId/comunicacion" element={<ComunicacionPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function setupServer(options: { atrasados?: typeof mockAtrasados; tracking?: unknown[] } = {}) {
  const { atrasados = mockAtrasados, tracking = [] } = options
  server.use(
    http.get('/api/comisiones/:id/analisis/atrasados', () => HttpResponse.json(atrasados)),
    http.get('/api/comunicaciones/:id/tracking', () => HttpResponse.json(tracking)),
    http.get('/api/comunicaciones/:id/preview/:alumnoId', () =>
      HttpResponse.json({ asunto: 'Recordatorio TP', cuerpo: 'Hola Ana, te faltan actividades.' }),
    ),
    http.post('/api/comunicaciones/enviar', () => HttpResponse.json({ ok: true })),
  )
}

describe('ComunicacionPage', () => {
  it('renders alumnos table with checkboxes', async () => {
    setupServer()
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    expect(screen.getByText(/Pérez/)).toBeInTheDocument()
    // Maestro checkbox
    expect(screen.getByTestId('checkbox-maestro-com')).toBeInTheDocument()
  })

  it('Previsualizar button is disabled when no selection', async () => {
    setupServer()
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    const btn = screen.getByRole('button', { name: /previsualizar/i })
    expect(btn).toBeDisabled()
  })

  it('checkbox maestro selects all alumnos', async () => {
    setupServer()
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('checkbox-maestro-com'))
    const previewBtn = screen.getByRole('button', { name: /previsualizar/i })
    expect(previewBtn).not.toBeDisabled()
    expect(previewBtn).toHaveTextContent('2')
  })

  it('opens preview modal after clicking Previsualizar', async () => {
    setupServer()
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('checkbox-maestro-com'))
    fireEvent.click(screen.getByRole('button', { name: /previsualizar/i }))
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
    expect(screen.getByText('Recordatorio TP')).toBeInTheDocument()
  })

  it('closing modal does not send any message', async () => {
    let sent = false
    setupServer()
    server.use(
      http.post('/api/comunicaciones/enviar', () => {
        sent = true
        return HttpResponse.json({ ok: true })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('checkbox-maestro-com'))
    fireEvent.click(screen.getByRole('button', { name: /previsualizar/i }))
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(sent).toBe(false)
  })

  it('shows error in modal when enviar fails', async () => {
    setupServer()
    server.use(
      http.post('/api/comunicaciones/enviar', () =>
        HttpResponse.json({ detail: 'Error de servidor' }, { status: 500 }),
      ),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/García/)).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('checkbox-maestro-com'))
    fireEvent.click(screen.getByRole('button', { name: /previsualizar/i }))
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /confirmar envío/i }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    // Modal stays open
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})
