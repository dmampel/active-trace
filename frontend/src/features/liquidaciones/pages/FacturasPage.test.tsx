import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthContext } from '@/features/auth/context/AuthContext'
import type { AuthContextValue } from '@/shared/types/auth'
import { FacturasPage } from './FacturasPage'

const mockUser = {
  id: 'u1', email: 'finanzas@example.com', nombre: 'Ana', apellido: 'Finanzas',
  roles: ['FINANZAS'], permissions: ['liquidaciones:ver'],
}

function makeCtx(): AuthContextValue {
  return {
    user: mockUser, session: null, isAuthenticated: true,
    hasPermission: (p) => mockUser.permissions.includes(p),
    setSession: () => undefined, clearSession: () => undefined,
  }
}

const mockFacturas = [
  {
    id: 'f1', docenteId: 'd1', docenteNombre: 'Marta', docenteApellido: 'Factura',
    periodo: '2024-06', detalle: 'Factura jun 2024', estado: 'pendiente',
    archivoUrl: null, archivoBytesSize: null, cargadaEn: '2024-06-10T00:00:00Z', pagadaEn: null,
  },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/liquidaciones/facturas']}>
        <AuthContext.Provider value={makeCtx()}>
          <Routes>
            <Route path="/liquidaciones/facturas" element={<FacturasPage />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FacturasPage', () => {
  it('lists facturas', async () => {
    server.use(http.get('/api/facturas', () => HttpResponse.json(mockFacturas)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Marta/)).toBeInTheDocument()
      expect(screen.getByText('pendiente')).toBeInTheDocument()
    })
  })

  it('filters by estado', async () => {
    server.use(http.get('/api/facturas', ({ request }) => {
      const url = new URL(request.url)
      const estado = url.searchParams.get('estado')
      const result = estado ? mockFacturas.filter((f) => f.estado === estado) : mockFacturas
      return HttpResponse.json(result)
    }))
    renderPage()
    await waitFor(() => expect(screen.getByText(/Marta/)).toBeInTheDocument())
    // Filter by abonada — empty
    fireEvent.change(screen.getByRole('combobox', { name: /estado/i }), { target: { value: 'abonada' } })
    await waitFor(() => expect(screen.queryByText(/Marta/)).not.toBeInTheDocument())
  })

  it('marcar abonada calls PATCH', async () => {
    let patched = false
    server.use(
      http.get('/api/facturas', () => HttpResponse.json(mockFacturas)),
      http.patch('/api/facturas/:id/estado', () => {
        patched = true
        return HttpResponse.json({ ...mockFacturas[0], estado: 'abonada' })
      }),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/Marta/)).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /marcar abonada/i }))
    await waitFor(() => expect(patched).toBe(true))
  })
})
