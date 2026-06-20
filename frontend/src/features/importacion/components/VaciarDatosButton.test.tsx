import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { VaciarDatosButton } from './VaciarDatosButton'

function renderComponent(comisionId = '42') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <VaciarDatosButton comisionId={comisionId} />
    </QueryClientProvider>,
  )
}

describe('VaciarDatosButton', () => {
  it('shows confirmation dialog when button is clicked', () => {
    renderComponent()
    fireEvent.click(screen.getByRole('button', { name: /vaciar datos/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/esta acción eliminará/i)).toBeInTheDocument()
  })

  it('cancelling dialog does not send any request', async () => {
    let requestMade = false
    server.use(
      http.delete('/api/comisiones/:id/calificaciones', () => {
        requestMade = true
        return HttpResponse.json({ ok: true })
      }),
    )
    renderComponent()
    fireEvent.click(screen.getByRole('button', { name: /vaciar datos/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(requestMade).toBe(false)
  })

  it('confirming dialog sends DELETE request and closes dialog', async () => {
    server.use(
      http.delete('/api/comisiones/:id/calificaciones', () => {
        return HttpResponse.json({ ok: true })
      }),
    )
    renderComponent()
    fireEvent.click(screen.getByRole('button', { name: /vaciar datos/i }))
    fireEvent.click(screen.getByRole('button', { name: /sí, vaciar/i }))
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})
