import type { PermissionString } from '@/shared/types/auth'

export interface MenuItem {
  label: string
  path: string
  permission: PermissionString
}

export const MENU_ITEMS: MenuItem[] = [
  // C-22 / C-23 features will add to this list
  { label: 'Inicio', path: '/', permission: 'dashboard:read' },
  { label: 'Comisiones', path: '/comisiones', permission: 'comisiones:read' },
  { label: 'Alumnos', path: '/alumnos', permission: 'alumnos:read' },
  { label: 'Comunicaciones', path: '/comunicaciones', permission: 'comunicacion:read' },
  { label: 'Equipos docentes', path: '/equipos', permission: 'equipos:read' },
  { label: 'Encuentros', path: '/encuentros', permission: 'encuentros:read' },
  { label: 'Coloquios', path: '/coloquios', permission: 'coloquios:read' },
  { label: 'Liquidaciones', path: '/liquidaciones', permission: 'liquidaciones:read' },
  { label: 'Auditoría', path: '/auditoria', permission: 'auditoria:read' },
]
