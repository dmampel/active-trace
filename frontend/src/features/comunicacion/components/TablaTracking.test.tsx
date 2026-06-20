import { render, screen } from '@testing-library/react'
import { TablaTracking } from './TablaTracking'
import type { MensajeTracking } from '../types'

const msgPendiente: MensajeTracking = {
  id: '1',
  destinatarioNombre: 'Ana García',
  destinatarioEmail: 'ana@t.com',
  estado: 'Pendiente',
  timestamp: '2024-01-15T10:00:00Z',
}

const msgOk: MensajeTracking = {
  id: '2',
  destinatarioNombre: 'Luis Pérez',
  destinatarioEmail: 'luis@t.com',
  estado: 'OK',
  timestamp: '2024-01-15T10:05:00Z',
}

const msgFallido: MensajeTracking = {
  id: '3',
  destinatarioNombre: 'Carmen Ruiz',
  destinatarioEmail: 'carmen@t.com',
  estado: 'Fallido',
  timestamp: '2024-01-15T10:10:00Z',
}

describe('TablaTracking', () => {
  it('shows empty state message when no mensajes', () => {
    render(<TablaTracking mensajes={[]} />)
    expect(screen.getByTestId('tracking-empty')).toBeInTheDocument()
    expect(screen.getByText(/aún no hay mensajes/i)).toBeInTheDocument()
  })

  it('renders one row per message', () => {
    render(<TablaTracking mensajes={[msgPendiente, msgOk]} />)
    expect(screen.getByText(/Ana García/)).toBeInTheDocument()
    expect(screen.getByText(/Luis Pérez/)).toBeInTheDocument()
  })

  it('shows badge for Pendiente state', () => {
    render(<TablaTracking mensajes={[msgPendiente]} />)
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
  })

  it('shows badge for OK state', () => {
    render(<TablaTracking mensajes={[msgOk]} />)
    expect(screen.getByText('OK')).toBeInTheDocument()
  })

  it('shows badge for Fallido state', () => {
    render(<TablaTracking mensajes={[msgFallido]} />)
    expect(screen.getByText('Fallido')).toBeInTheDocument()
  })

  it('shows no action buttons (read-only for PROFESOR)', () => {
    render(<TablaTracking mensajes={[msgPendiente, msgOk]} />)
    // No buttons should exist in the table
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
