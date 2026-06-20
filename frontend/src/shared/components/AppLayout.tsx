import { Outlet, NavLink, useMatch } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { MENU_ITEMS } from '@/app/menuItems'

export function AppLayout() {
  const { user, hasPermission } = useAuth()
  const { logout, isLoading } = useLogout()

  const comisionMatch = useMatch('/comision/:comisionId/*')
  const comisionId = comisionMatch?.params.comisionId

  const visibleItems = MENU_ITEMS.filter((item) => hasPermission(item.permission))

  const canImport = hasPermission('calificaciones:importar')
  const isProfesorOrTutor =
    user?.roles.some((r) => r === 'PROFESOR' || r === 'TUTOR') ?? false

  return (
    <div className="flex min-h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow-md flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800">active-trace</h1>
        </div>
        <nav className="flex-1 py-4">
          <ul className="space-y-1 px-3">
            {visibleItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
            {/* Contextual comisión navigation for PROFESOR and TUTOR */}
            {comisionId && isProfesorOrTutor && (
              <>
                <li className="mt-4 px-4 pb-1">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Comisión
                  </span>
                </li>
                {canImport && (
                  <li>
                    <NavLink
                      to={`/comision/${comisionId}/importar`}
                      className={({ isActive }) =>
                        `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                        }`
                      }
                    >
                      Importar calificaciones
                    </NavLink>
                  </li>
                )}
                <li>
                  <NavLink
                    to={`/comision/${comisionId}/analisis`}
                    className={({ isActive }) =>
                      `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-100 text-indigo-700'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`
                    }
                  >
                    Análisis
                  </NavLink>
                </li>
                <li>
                  <NavLink
                    to={`/comision/${comisionId}/comunicacion`}
                    className={({ isActive }) =>
                      `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-100 text-indigo-700'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`
                    }
                  >
                    Comunicaciones
                  </NavLink>
                </li>
                <li>
                  <NavLink
                    to={`/comision/${comisionId}/monitor`}
                    className={({ isActive }) =>
                      `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-100 text-indigo-700'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`
                    }
                  >
                    Monitor
                  </NavLink>
                </li>
              </>
            )}
          </ul>
        </nav>
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-indigo-200 flex items-center justify-center">
              <span className="text-xs font-semibold text-indigo-700">
                {user?.nombre?.[0]?.toUpperCase() ?? '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">
                {user ? `${user.nombre} ${user.apellido}` : '—'}
              </p>
              <p className="text-xs text-gray-500 truncate">{user?.email ?? ''}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            disabled={isLoading}
            className="w-full px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Cerrando sesión…' : 'Cerrar sesión'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
