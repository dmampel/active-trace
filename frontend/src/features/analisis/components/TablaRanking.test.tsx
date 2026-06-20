import { render, screen, fireEvent } from '@testing-library/react'
import { TablaRanking } from './TablaRanking'
import type { AlumnoRanking } from '../types'

const mockAlumnos: AlumnoRanking[] = [
  { id: '1', nombre: 'Ana', apellido: 'García', email: 'ana@t.com', actividadesAprobadas: 5, nota: 9 },
  { id: '2', nombre: 'Beto', apellido: 'López', email: 'beto@t.com', actividadesAprobadas: 8, nota: 8 },
  { id: '3', nombre: 'Carla', apellido: 'Díaz', email: 'carla@t.com', actividadesAprobadas: 0, nota: 4 },
]

describe('TablaRanking', () => {
  it('excludes alumnos with zero approved activities', () => {
    render(<TablaRanking alumnos={mockAlumnos} />)
    expect(screen.queryByText(/Díaz/)).not.toBeInTheDocument()
  })

  it('renders alumnos with approved activities', () => {
    render(<TablaRanking alumnos={mockAlumnos} />)
    expect(screen.getByText(/García/)).toBeInTheDocument()
    expect(screen.getByText(/López/)).toBeInTheDocument()
  })

  it('orders by actividadesAprobadas descending by default', () => {
    render(<TablaRanking alumnos={mockAlumnos} />)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('López') // 8 aprobadas first
    expect(rows[2]).toHaveTextContent('García') // 5 aprobadas second
  })

  it('toggles sort direction when same column header is clicked', () => {
    render(<TablaRanking alumnos={mockAlumnos} />)
    fireEvent.click(screen.getByText(/aprobadas/i))
    const rows = screen.getAllByRole('row')
    // Now ascending: García (5) first, López (8) second
    expect(rows[1]).toHaveTextContent('García')
    expect(rows[2]).toHaveTextContent('López')
  })
})
