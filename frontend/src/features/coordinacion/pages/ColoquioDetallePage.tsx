import { useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import {
  useReservasConvocatoria,
  useRegistroAcademico,
  useImportarPadronColoquio,
} from '../hooks/useCoordinacion'

type TabId = 'agenda' | 'reservas' | 'registro'

const TABS: { id: TabId; label: string }[] = [
  { id: 'agenda', label: 'Agenda' },
  { id: 'reservas', label: 'Reservas' },
  { id: 'registro', label: 'Registro académico' },
]

export function ColoquioDetallePage() {
  const { convocatoriaId } = useParams<{ convocatoriaId: string }>()
  const id = convocatoriaId ?? ''
  const [activeTab, setActiveTab] = useState<TabId>('agenda')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: reservas = [], isLoading: loadingReservas } = useReservasConvocatoria(id)
  const { data: registro = [], isLoading: loadingRegistro } = useRegistroAcademico(id)
  const importarPadron = useImportarPadronColoquio(id)

  function handleImportarClick() {
    fileInputRef.current?.click()
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await importarPadron.mutateAsync(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Detalle de Convocatoria</h1>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={handleImportarClick}
            disabled={importarPadron.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            aria-label="Importar padrón"
          >
            {importarPadron.isPending ? 'Importando…' : 'Importar padrón'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div role="tablist" className="flex border-b border-gray-200 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => { setActiveTab(tab.id) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Agenda tab */}
      {activeTab === 'agenda' && (
        <div role="tabpanel">
          <p className="text-sm text-gray-600 mb-4">
            Reservas activas para esta convocatoria.
          </p>
          {loadingReservas && <p className="text-gray-500 text-sm">Cargando…</p>}
          {!loadingReservas && reservas.length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <p>Sin reservas activas.</p>
            </div>
          )}
          {!loadingReservas && reservas.length > 0 && (
            <table className="w-full text-sm bg-white rounded-lg border border-gray-200 overflow-hidden">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Alumno
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Día
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Cupo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Estado
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reservas.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 text-gray-900">
                      {r.alumnoNombre} {r.alumnoApellido}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{r.dia}</td>
                    <td className="px-4 py-3 text-gray-600">{r.cupo}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">
                        {r.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Reservas tab */}
      {activeTab === 'reservas' && (
        <div role="tabpanel">
          <p className="text-sm text-gray-600">Historial de reservas.</p>
        </div>
      )}

      {/* Registro académico tab */}
      {activeTab === 'registro' && (
        <div role="tabpanel">
          {loadingRegistro && <p className="text-gray-500 text-sm">Cargando…</p>}
          {!loadingRegistro && registro.length === 0 && (
            <div className="text-center py-8 text-gray-400">
              <p className="text-lg">Sin notas cargadas</p>
              <p className="text-sm mt-1">
                Aún no hay resultados académicos registrados para esta convocatoria.
              </p>
            </div>
          )}
          {!loadingRegistro && registro.length > 0 && (
            <table className="w-full text-sm bg-white rounded-lg border border-gray-200 overflow-hidden">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Alumno
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Nota
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Resultado
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {registro.map((r) => (
                  <tr key={r.alumnoId}>
                    <td className="px-4 py-3 text-gray-900">
                      {r.alumnoNombre} {r.alumnoApellido}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{r.nota ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          r.resultado === 'aprobado'
                            ? 'bg-green-100 text-green-700'
                            : r.resultado === 'desaprobado'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {r.resultado ?? 'pendiente'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
