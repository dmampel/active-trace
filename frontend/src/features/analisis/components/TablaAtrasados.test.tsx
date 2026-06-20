import { render, screen, fireEvent } from '@testing-library/react'
import { TablaAtrasados } from './TablaAtrasados'
import type { AlumnoAtrasado } from '../types'

const mockAlumnos: AlumnoAtrasado[] = [
  {
    id: '1',
    nombre: 'Ana',
    apellido: 'García',
    email: 'ana@test.com',
    actividadesFaltantes: 3,
    nota: 5,
  },
  {
    id: '2',
    nombre: 'Bernardo',
    apellido: 'López',
    email: 'blopez@test.com',
    actividadesFaltantes: 1,
    nota: 7,
  },
]

describe('TablaAtrasados', () => {
  it('shows empty state message when no alumnos', () => {
    render(<TablaAtrasados alumnos={[]} />)
    expect(screen.getByText(/todos los alumnos están al día/i)).toBeInTheDocument()
  })

  it('renders all alumnos when no filter applied', () => {
    render(<TablaAtrasados alumnos={mockAlumnos} />)
    expect(screen.getByText(/García/)).toBeInTheDocument()
    expect(screen.getByText(/López/)).toBeInTheDocument()
  })

  it('filters by nombre/correo text (case insensitive)', () => {
    render(<TablaAtrasados alumnos={mockAlumnos} />)
    const input = screen.getByRole('textbox', { name: /buscar/i })
    fireEvent.change(input, { target: { value: 'ana' } })
    expect(screen.getByText(/García/)).toBeInTheDocument()
    expect(screen.queryByText(/López/)).not.toBeInTheDocument()
  })

  it('filters by email', () => {
    render(<TablaAtrasados alumnos={mockAlumnos} />)
    const input = screen.getByRole('textbox', { name: /buscar/i })
    fireEvent.change(input, { target: { value: 'blopez' } })
    expect(screen.getByText(/López/)).toBeInTheDocument()
    expect(screen.queryByText(/García/)).not.toBeInTheDocument()
  })

  it('sorts by column when header is clicked', () => {
    render(<TablaAtrasados alumnos={mockAlumnos} />)
    // Click "Actividades faltantes" header
    fireEvent.click(screen.getByText(/actividades faltantes/i))
    const rows = screen.getAllByRole('row')
    // First data row (index 1 since index 0 is header)
    expect(rows[1]).toHaveTextContent('López')
  })
})
