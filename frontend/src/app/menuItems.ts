import type { PermissionString } from '@/shared/types/auth'

export interface MenuItem {
  label: string
  path: string
  permission: PermissionString
}

export const MENU_ITEMS: MenuItem[] = [
  // General
  { label: 'Inicio', path: '/', permission: 'dashboard:read' },
  { label: 'Comisiones', path: '/comisiones', permission: 'comisiones:read' },
  { label: 'Alumnos', path: '/alumnos', permission: 'alumnos:read' },

  // Docente
  { label: 'Mis tareas', path: '/tareas', permission: 'tareas:ver' },

  // Equipos (C-23)
  { label: 'Mis equipos', path: '/equipos', permission: 'equipos:ver' },
  { label: 'Asignaciones (admin)', path: '/equipos/admin', permission: 'equipos:admin' },
  { label: 'Asignación masiva', path: '/equipos/masiva', permission: 'equipos:admin' },
  { label: 'Clonar equipo', path: '/equipos/clonar', permission: 'equipos:admin' },

  // Avisos (C-23)
  { label: 'Avisos', path: '/avisos', permission: 'avisos:admin' },

  // Coordinación (C-23)
  { label: 'Tareas (coord)', path: '/coordinacion/tareas', permission: 'tareas:admin' },
  { label: 'Monitor general', path: '/coordinacion/monitores', permission: 'atrasados:ver' },
  {
    label: 'Monitor seguimiento',
    path: '/coordinacion/monitores/seguimiento',
    permission: 'atrasados:ver',
  },
  { label: 'Encuentros (admin)', path: '/coordinacion/encuentros', permission: 'encuentros:ver' },
  { label: 'Coloquios', path: '/coordinacion/coloquios', permission: 'coloquios:admin' },
  {
    label: 'Aprobar comunicaciones',
    path: '/coordinacion/comunicaciones/aprobacion',
    permission: 'comunicacion:aprobar',
  },

  // Legacy paths
  { label: 'Liquidaciones', path: '/liquidaciones', permission: 'liquidaciones:read' },
  { label: 'Auditoría', path: '/auditoria', permission: 'auditoria:read' },
]
