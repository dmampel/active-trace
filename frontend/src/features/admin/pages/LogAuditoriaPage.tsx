import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLogAuditoria } from '../hooks/useAdmin'
import type { FiltrosAuditoria } from '../types'

export function LogAuditoriaPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({
    desde: searchParams.get('desde') ?? '',
    hasta: searchParams.get('hasta') ?? '',
    materia: searchParams.get('materia') ?? '',
    usuario: searchParams.get('usuario') ?? '',
    estado: searchParams.get('estado') ?? '',
  })

  const { data: log = [], isLoading } = useLogAuditoria(
    Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '')),
  )

  function updateFiltro(key: keyof FiltrosAuditoria, value: string) {
    const next = { ...filtros, [key]: value }
    setFiltros(next)
    const params = Object.fromEntries(Object.entries(next).filter(([, v]) => v !== ''))
    setSearchParams(params)
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Log de Auditoría</h1>

      {/* Filtros */}
      <div className="flex flex-wrap gap-4 mb-6">
        {[
          { id: 'log-desde', label: 'Desde', key: 'desde' as const, type: 'date' },
          { id: 'log-hasta', label: 'Hasta', key: 'hasta' as const, type: 'date' },
          { id: 'log-materia', label: 'Materia', key: 'materia' as const, type: 'text' },
          { id: 'log-usuario', label: 'Usuario', key: 'usuario' as const, type: 'text' },
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
      ) : (
        <>
          <p className="text-xs text-gray-400 mb-2">{log.length} registros</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse min-w-[800px]">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                  <th className="py-2 pr-4">Fecha</th>
                  <th className="py-2 pr-4">Usuario</th>
                  <th className="py-2 pr-4">Acción</th>
                  <th className="py-2 pr-4">Materia</th>
                  <th className="py-2 pr-4 text-right">Filas</th>
                  <th className="py-2">IP</th>
                </tr>
              </thead>
              <tbody>
                {log.map((entry) => (
                  <tr key={entry.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 pr-4 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(entry.fecha).toLocaleString('es-AR')}
                    </td>
                    <td className="py-2 pr-4">{entry.usuarioApellido}, {entry.usuarioNombre}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{entry.accion}</td>
                    <td className="py-2 pr-4 text-gray-500">{entry.materia ?? '—'}</td>
                    <td className="py-2 pr-4 text-right">{entry.filasAfectadas}</td>
                    <td className="py-2 text-xs text-gray-400">{entry.ip}</td>
                  </tr>
                ))}
                {log.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">Sin registros</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
