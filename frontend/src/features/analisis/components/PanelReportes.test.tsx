import { render, screen } from '@testing-library/react'
import { PanelReportes } from './PanelReportes'
import type { ReportesMetricas } from '../types'

const mockMetricas: ReportesMetricas = {
  totalAlumnos: 30,
  porcentajeAlDia: 73.3,
  actividadesIncluidas: 5,
  promedioGeneral: 6.75,
}

describe('PanelReportes', () => {
  it('renders 4 metric cards', () => {
    render(<PanelReportes metricas={mockMetricas} />)
    expect(screen.getByText('Total alumnos')).toBeInTheDocument()
    expect(screen.getByText('% al día')).toBeInTheDocument()
    expect(screen.getByText('Actividades incluidas')).toBeInTheDocument()
    expect(screen.getByText('Promedio general')).toBeInTheDocument()
  })

  it('displays correct values for each metric', () => {
    render(<PanelReportes metricas={mockMetricas} />)
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.getByText('73.3%')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('6.75')).toBeInTheDocument()
  })

  it('reflects updated metrics when props change', () => {
    const { rerender } = render(<PanelReportes metricas={mockMetricas} />)
    const newMetricas: ReportesMetricas = {
      totalAlumnos: 30,
      porcentajeAlDia: 80.0,
      actividadesIncluidas: 5,
      promedioGeneral: 7.5,
    }
    rerender(<PanelReportes metricas={newMetricas} />)
    expect(screen.getByText('80.0%')).toBeInTheDocument()
    expect(screen.getByText('7.50')).toBeInTheDocument()
  })
})
