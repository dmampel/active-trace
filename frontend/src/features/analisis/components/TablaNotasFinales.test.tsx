import { render, screen, fireEvent } from '@testing-library/react'
import { TablaNotasFinales } from './TablaNotasFinales'
import type { NotaFinal } from '../types'

const mockNotas: NotaFinal[] = [
  { id: '1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', notaFinal: 8.5 },
  { id: '2', nombre: 'Beto', apellido: 'López', email: 'beto@t.com', notaFinal: 6.0 },
]

describe('TablaNotasFinales', () => {
  it('renders one row per alumno', () => {
    render(<TablaNotasFinales notas={mockNotas} />)
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(3) // header + 2 data rows
  })

  it('shows each alumno exactly once', () => {
    render(<TablaNotasFinales notas={mockNotas} />)
    expect(screen.getByText(/García/)).toBeInTheDocument()
    expect(screen.getByText(/López/)).toBeInTheDocument()
  })

  it('shows Exportar CSV button enabled when there are notes', () => {
    render(<TablaNotasFinales notas={mockNotas} />)
    const btn = screen.getByRole('button', { name: /exportar csv/i })
    expect(btn).not.toBeDisabled()
  })

  it('shows Exportar CSV button disabled when no notes', () => {
    render(<TablaNotasFinales notas={[]} />)
    expect(screen.getByRole('button', { name: /exportar csv/i })).toBeDisabled()
  })

  it('clicking Exportar CSV triggers download (does not throw)', () => {
    const createObjectURL = vi.fn(() => 'blob:url')
    const revokeObjectURL = vi.fn()
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    render(<TablaNotasFinales notas={mockNotas} />)
    const btn = screen.getByRole('button', { name: /exportar csv/i })
    fireEvent.click(btn)
    expect(createObjectURL).toHaveBeenCalledTimes(1)
  })
})
