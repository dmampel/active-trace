import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { ImportarCalificacionesPage } from './ImportarCalificacionesPage'

const mockUser = {
  id: '1',
  email: 'prof@example.com',
  nombre: 'María',
  apellido: 'González',
  roles: ['PROFESOR'],
  permissions: ['calificaciones:importar'],
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

function renderPage(comisionId = '42') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/comision/${comisionId}/importar`]}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/comision/:comisionId/importar" element={<ImportarCalificacionesPage />} />
            <Route path="/comision/:comisionId/analisis" element={<div>Analisis Page</div>} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ImportarCalificacionesPage', () => {
  it('shows step 1 with file input on initial render', () => {
    renderPage()
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument()
    expect(screen.getByTestId('file-input')).toBeInTheDocument()
  })

  it('shows step indicator with step 1 active', () => {
    renderPage()
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument()
  })

  it('shows upload progress after file selection (mocked)', async () => {
    server.use(
      http.post('/api/comisiones/:id/calificaciones/preview', () => {
        return HttpResponse.json({ actividades: [{ id: 'a1', nombre: 'TP1', tipo: 'tarea' }] })
      }),
    )
    renderPage()
    const fileInput = screen.getByTestId('file-input')
    const file = new File(['content'], 'grades.csv', { type: 'text/csv' })
    fireEvent.change(fileInput, { target: { files: [file] } })
    await waitFor(() => {
      expect(screen.getByText('Paso 2 de 4')).toBeInTheDocument()
    })
  })

  it('shows error when backend returns 413', async () => {
    server.use(
      http.post('/api/comisiones/:id/calificaciones/preview', () => {
        return HttpResponse.json({ detail: 'too large' }, { status: 413 })
      }),
    )
    renderPage()
    const fileInput = screen.getByTestId('file-input')
    const file = new File(['content'], 'grades.csv', { type: 'text/csv' })
    fireEvent.change(fileInput, { target: { files: [file] } })
    await waitFor(() => {
      expect(screen.getByText(/tamaño máximo/i)).toBeInTheDocument()
    })
    // remains on step 1
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument()
  })

  it('advances through steps when activities are selected', async () => {
    server.use(
      http.post('/api/comisiones/:id/calificaciones/preview', () => {
        return HttpResponse.json({
          actividades: [
            { id: 'a1', nombre: 'TP1', tipo: 'tarea' },
            { id: 'a2', nombre: 'Examen', tipo: 'examen' },
          ],
        })
      }),
    )
    renderPage()
    const fileInput = screen.getByTestId('file-input')
    const file = new File(['content'], 'grades.csv', { type: 'text/csv' })
    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('Paso 2 de 4')).toBeInTheDocument()
    })

    // Step 2: Continue with all activities selected by default
    const continuarBtn = screen.getByRole('button', { name: /continuar/i })
    expect(continuarBtn).not.toBeDisabled()
    fireEvent.click(continuarBtn)

    await waitFor(() => {
      expect(screen.getByText('Paso 3 de 4')).toBeInTheDocument()
    })
  })

  it('disables Continue button on step 2 when no activities selected', async () => {
    server.use(
      http.post('/api/comisiones/:id/calificaciones/preview', () => {
        return HttpResponse.json({ actividades: [{ id: 'a1', nombre: 'TP1', tipo: 'tarea' }] })
      }),
    )
    renderPage()
    const fileInput = screen.getByTestId('file-input')
    fireEvent.change(fileInput, { target: { files: [new File(['x'], 'f.csv')] } })

    await waitFor(() => {
      expect(screen.getByText('Paso 2 de 4')).toBeInTheDocument()
    })

    // Deselect all
    const maestro = screen.getByTestId('checkbox-maestro')
    fireEvent.click(maestro) // deselects all
    const continuar = screen.getByRole('button', { name: /continuar/i })
    expect(continuar).toBeDisabled()
  })
})
