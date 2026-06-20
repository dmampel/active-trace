import type { ReportesMetricas } from '../types'

interface MetricaCardProps {
  label: string
  valor: string | number
}

function MetricaCard({ label, valor }: MetricaCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{valor}</p>
    </div>
  )
}

interface PanelReportesProps {
  metricas: ReportesMetricas
}

export function PanelReportes({ metricas }: PanelReportesProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <MetricaCard label="Total alumnos" valor={metricas.totalAlumnos} />
      <MetricaCard
        label="% al día"
        valor={`${metricas.porcentajeAlDia.toFixed(1)}%`}
      />
      <MetricaCard label="Actividades incluidas" valor={metricas.actividadesIncluidas} />
      <MetricaCard
        label="Promedio general"
        valor={metricas.promedioGeneral.toFixed(2)}
      />
    </div>
  )
}
