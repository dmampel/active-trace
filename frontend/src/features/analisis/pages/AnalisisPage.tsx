import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useAtrasados, useRanking, useNotasFinales, useReportes, useUmbral } from '../hooks/useAnalisis'
import { TablaAtrasados } from '../components/TablaAtrasados'
import { TablaRanking } from '../components/TablaRanking'
import { PanelReportes } from '../components/PanelReportes'
import { TablaNotasFinales, exportNotasFinalesCsv } from '../components/TablaNotasFinales'
import { VaciarDatosButton } from '@/features/importacion/components/VaciarDatosButton'
import { TablaFinalizacion, exportFinalizacionCsv } from '@/features/importacion/components/TablaFinalizacion'
import { useFinalizacionActividades } from '@/features/importacion/hooks/useFinalizacionActividades'
import type { AnalisisTab } from '../types'

export function AnalisisPage() {
  const { comisionId = '' } = useParams()
  const { hasPermission } = useAuth()
  const canImport = hasPermission('calificaciones:importar')

  const [activeTab, setActiveTab] = useState<AnalisisTab>('atrasados')
  const [editingUmbral, setEditingUmbral] = useState(false)
  const [umbralInput, setUmbralInput] = useState('')

  const { umbral, isLoading: umbralLoading, updateUmbral, isUpdating } = useUmbral(comisionId)
  const { data: atrasados = [], isLoading: atrasadosLoading } = useAtrasados(comisionId)
  const { data: ranking = [], isLoading: rankingLoading } = useRanking(comisionId)
  const { data: notas = [], isLoading: notasLoading } = useNotasFinales(comisionId)
  const { data: reportes, isLoading: reportesLoading } = useReportes(comisionId)

  const { items: finalizacionItems, isLoading: finLoading, upload: uploadFinalizacion } = useFinalizacionActividades()

  const hayDatos = atrasados.length > 0 || ranking.length > 0 || notas.length > 0

  const handleUmbralSave = async () => {
    const val = Number(umbralInput)
    if (val >= 1 && val <= 100) {
      await updateUmbral(val)
      setEditingUmbral(false)
    }
  }

  const tabs: { key: AnalisisTab; label: string }[] = [
    { key: 'atrasados', label: 'Atrasados' },
    { key: 'ranking', label: 'Ranking' },
    { key: 'reportes', label: 'Reportes' },
    { key: 'notas', label: 'Notas finales' },
  ]

  if (!hayDatos && !atrasadosLoading) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Análisis de la comisión</h1>
        <p className="text-gray-500 mb-6">Aún no hay datos para esta comisión</p>
        <Link
          to={`/comision/${comisionId}/importar`}
          className="px-5 py-2.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          Importar calificaciones
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Análisis de la comisión</h1>
          {!umbralLoading && umbral !== undefined && (
            <div className="flex items-center gap-2 mt-1">
              {editingUmbral ? (
                <>
                  <input
                    type="number"
                    value={umbralInput}
                    onChange={(e) => setUmbralInput(e.target.value)}
                    min={1}
                    max={100}
                    className="border border-gray-300 rounded px-2 py-1 text-sm w-20"
                    aria-label="Nuevo umbral"
                  />
                  <button
                    type="button"
                    onClick={() => void handleUmbralSave()}
                    disabled={isUpdating}
                    className="text-sm text-indigo-600 hover:underline disabled:opacity-50"
                  >
                    Guardar
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingUmbral(false)}
                    className="text-sm text-gray-400 hover:underline"
                  >
                    Cancelar
                  </button>
                </>
              ) : (
                <>
                  <span className="text-sm text-gray-600">
                    Umbral de aprobación: <strong>{umbral}%</strong>
                  </span>
                  {canImport && (
                    <button
                      type="button"
                      onClick={() => {
                        setUmbralInput(String(umbral))
                        setEditingUmbral(true)
                      }}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      Editar
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
        {canImport && <VaciarDatosButton comisionId={comisionId} />}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'atrasados' && (
          atrasadosLoading ? <p>Cargando…</p> : <TablaAtrasados alumnos={atrasados} />
        )}
        {activeTab === 'ranking' && (
          rankingLoading ? <p>Cargando…</p> : <TablaRanking alumnos={ranking} />
        )}
        {activeTab === 'reportes' && (
          reportesLoading || !reportes ? (
            <p>Cargando…</p>
          ) : (
            <PanelReportes metricas={reportes} />
          )
        )}
        {activeTab === 'notas' && (
          notasLoading ? (
            <p>Cargando…</p>
          ) : (
            <TablaNotasFinales
              notas={notas}
            />
          )
        )}
      </div>

      {/* Reporte de finalización */}
      <div className="mt-8 border-t border-gray-200 pt-6">
        <h2 className="text-lg font-semibold mb-3">Reporte de finalización</h2>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          disabled={finLoading}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void uploadFinalizacion(comisionId, file)
          }}
          className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100 mb-4"
          data-testid="finalizacion-input"
        />
        <TablaFinalizacion
          items={finalizacionItems}
          onExportCsv={() => exportFinalizacionCsv(finalizacionItems)}
        />
      </div>
    </div>
  )
}
