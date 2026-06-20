import { useState } from 'react'
import { useEquiposDocente } from '../hooks/useEquipos'
import type { Equipo } from '../types'

type TabId = 'mis-asignaciones' | 'actividad' | 'comunicaciones'

const TABS: { id: TabId; label: string }[] = [
  { id: 'mis-asignaciones', label: 'Mis asignaciones' },
  { id: 'actividad', label: 'Actividad' },
  { id: 'comunicaciones', label: 'Comunicaciones' },
]

function EquipoRow({ equipo }: { equipo: Equipo }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-3">
      <h3 className="font-semibold text-gray-800">{equipo.materiaNombre}</h3>
      <p className="text-sm text-gray-500">
        {equipo.carreraNombre} — Cohorte {equipo.cohorteNombre}
      </p>
      <div className="mt-2 space-y-1">
        {equipo.asignaciones.map((a) => (
          <div key={a.id} className="flex items-center gap-2 text-sm">
            <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-medium">
              {a.rol}
            </span>
            <span className="text-gray-600">
              {a.docenteNombre} {a.docenteApellido}
            </span>
            <span
              className={`ml-auto px-2 py-0.5 rounded-full text-xs font-medium ${
                a.estado === 'activa'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {a.estado}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function EquiposPage() {
  const [activeTab, setActiveTab] = useState<TabId>('mis-asignaciones')
  const { data: equipos = [], isLoading } = useEquiposDocente()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Mis Equipos</h1>

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

      {/* Tab panels */}
      {activeTab === 'mis-asignaciones' && (
        <div role="tabpanel">
          {isLoading && <p className="text-gray-500">Cargando equipos…</p>}
          {!isLoading && equipos.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg">Sin asignaciones activas</p>
              <p className="text-sm mt-1">No tenés comisiones asignadas en este período.</p>
            </div>
          )}
          {!isLoading && equipos.map((e) => <EquipoRow key={e.id} equipo={e} />)}
        </div>
      )}

      {activeTab === 'actividad' && (
        <div role="tabpanel">
          <p className="text-gray-500 text-sm">Actividad de los alumnos en tus comisiones.</p>
        </div>
      )}

      {activeTab === 'comunicaciones' && (
        <div role="tabpanel">
          <p className="text-gray-500 text-sm">Comunicaciones del equipo docente.</p>
        </div>
      )}
    </div>
  )
}
