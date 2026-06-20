import { render, screen, fireEvent } from '@testing-library/react'
import { TablaFinalizacion } from './TablaFinalizacion'
import type { FinalizacionItem } from '../types'

const mockItems: FinalizacionItem[] = [
  { alumnoNombre: 'Ana García', alumnoEmail: 'ana@test.com', actividad: 'TP1', estado: 'Entregado' },
  { alumnoNombre: 'Luis Pérez', alumnoEmail: 'luis@test.com', actividad: 'TP2', estado: 'Entregado' },
]

describe('TablaFinalizacion', () => {
  it('shows empty state message when items is empty', () => {
    render(<TablaFinalizacion items={[]} onExportCsv={() => undefined} />)
    expect(screen.getByText(/no se detectaron entregas/i)).toBeInTheDocument()
  })

  it('disables Exportar CSV button when empty', () => {
    render(<TablaFinalizacion items={[]} onExportCsv={() => undefined} />)
    expect(screen.getByRole('button', { name: /exportar csv/i })).toBeDisabled()
  })

  it('renders table rows when items are provided', () => {
    render(<TablaFinalizacion items={mockItems} onExportCsv={() => undefined} />)
    expect(screen.getByText(/Ana García/)).toBeInTheDocument()
    expect(screen.getByText(/Luis Pérez/)).toBeInTheDocument()
  })

  it('enables Exportar CSV button when items exist and calls handler on click', () => {
    const onExport = vi.fn()
    render(<TablaFinalizacion items={mockItems} onExportCsv={onExport} />)
    const btn = screen.getByRole('button', { name: /exportar csv/i })
    expect(btn).not.toBeDisabled()
    fireEvent.click(btn)
    expect(onExport).toHaveBeenCalledTimes(1)
  })
})
