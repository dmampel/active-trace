import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { usePanelAuditoria } from '../hooks/useAdmin'
import type { FiltrosAuditoria } from '../types'

export function AuditoriaPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({
    desde: searchParams.get('desde') ?? '',
    hasta: searchParams.get('hasta') ?? '',
    materia: searchParams.get('materia') ?? '',
    usuario: searchParams.get('usuario') ?? '',
  })

  const { data: panel, isLoading } = usePanelAuditoria(
    Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '')),
  )

  function updateFiltro(key: keyof FiltrosAuditoria, value: string) {
    const next = { ...filtros, [key]: value }
    setFiltros(next)
    const params = Object.fromEntries(Object.entries(next).filter(([, v]) => v !== ''))
    setSearchParams(params)
  }

  const maxAcciones = panel ? Math.max(...panel.accionesPorDia.map((a) => a.total), 1) : 1

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Auditoría e Interacciones</h1>

      {/* Filtros */}
      <div className="flex flex-wrap gap-4 mb-6">
        {[
          { id: 'aud-desde', label: 'Desde', key: 'desde' as const, type: 'date' },
          { id: 'aud-hasta', label: 'Hasta', key: 'hasta' as const, type: 'date' },
          { id: 'aud-materia', label: 'Materia', key: 'materia' as const, type: 'text' },
          { id: 'aud-usuario', label: 'Usuario', key: 'usuario' as const, type: 'text' },
        ].map(({ id, label, key, type }) => (
          <div key={key}>
            <label htmlFor={id} className="block text-xs text-gray-600 mb-1">{label}</label>
            <input
              id={id}
              aria-label={label}
              type={type}
              value={filtros[key] ?? ''}
              onChange={(e) => updateFiltro(key, e.target.value)}
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm w-44"
            />
          </div>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : panel ? (
        <div className="space-y-8">
          {/* Acciones por día */}
          <section>
            <h2 className="text-base font-semibold text-gray-700 mb-3">Acciones por día</h2>
            <div className="space-y-1.5">
              {panel.accionesPorDia.map((a) => (
                <div key={a.fecha} className="flex items-center gap-3 text-sm">
                  <span className="w-24 text-gray-500 text-xs shrink-0">{a.fecha}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-500 h-full rounded-full"
                      style={{ width: `${(a.total / maxAcciones) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs text-gray-600">{a.total}</span>
                </div>
              ))}
              {panel.accionesPorDia.length === 0 && <p className="text-sm text-gray-400">Sin datos</p>}
            </div>
          </section>

          {/* Estado de comunicaciones */}
          <section>
            <h2 className="text-base font-semibold text-gray-700 mb-3">Estado de comunicaciones por docente</h2>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                  <th className="py-1 pr-4">Docente</th>
                  <th className="py-1 pr-4 text-right">Pendiente</th>
                  <th className="py-1 pr-4 text-right">Enviado</th>
                  <th className="py-1 pr-4 text-right">Fallido</th>
                  <th className="py-1 text-right">Cancelado</th>
                </tr>
              </thead>
              <tbody>
                {panel.estadoComunicaciones.map((ec) => (
                  <tr key={ec.docenteId} className="border-b border-gray-100">
                    <td className="py-2 pr-4">{ec.docenteApellido}, {ec.docenteNombre}</td>
                    <td className="py-2 pr-4 text-right">{ec.pendiente}</td>
                    <td className="py-2 pr-4 text-right text-green-600">{ec.enviado}</td>
                    <td className="py-2 pr-4 text-right text-red-600">{ec.fallido}</td>
                    <td className="py-2 text-right text-gray-400">{ec.cancelado}</td>
                  </tr>
                ))}
                {panel.estadoComunicaciones.length === 0 && (
                  <tr><td colSpan={5} className="py-4 text-center text-gray-400 text-sm">Sin datos</td></tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Últimas acciones */}
          <section>
            <h2 className="text-base font-semibold text-gray-700 mb-3">Últimas acciones</h2>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                  <th className="py-1 pr-4">Fecha</th>
                  <th className="py-1 pr-4">Usuario</th>
                  <th className="py-1 pr-4">Acción</th>
                  <th className="py-1 pr-4">Materia</th>
                  <th className="py-1 pr-4 text-right">Filas</th>
                  <th className="py-1">IP</th>
                </tr>
              </thead>
              <tbody>
                {panel.ultimasAcciones.map((a) => (
                  <tr key={a.id} className="border-b border-gray-100">
                    <td className="py-2 pr-4 text-xs text-gray-500">{new Date(a.fecha).toLocaleString('es-AR')}</td>
                    <td className="py-2 pr-4">{a.usuarioApellido}, {a.usuarioNombre}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{a.accion}</td>
                    <td className="py-2 pr-4 text-gray-500">{a.materia ?? '—'}</td>
                    <td className="py-2 pr-4 text-right">{a.filasAfectadas}</td>
                    <td className="py-2 text-xs text-gray-400">{a.ip}</td>
                  </tr>
                ))}
                {panel.ultimasAcciones.length === 0 && (
                  <tr><td colSpan={6} className="py-4 text-center text-gray-400 text-sm">Sin acciones</td></tr>
                )}
              </tbody>
            </table>
          </section>
        </div>
      ) : null}
    </div>
  )
}
