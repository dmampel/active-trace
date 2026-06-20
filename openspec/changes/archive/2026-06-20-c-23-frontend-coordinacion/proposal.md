## Why

El shell SPA (C-21) y el módulo docente/académico (C-22) están completos. El coordinador y el admin carecen de interfaz para las operaciones que más los diferencian: gestión de equipos, publicación de avisos, workflow de tareas y supervisión transversal. C-23 construye todas esas pantallas sobre la misma base de C-21, habilitando el flujo de setup de cuatrimestre (FL-03) de extremo a extremo.

## What Changes

- **Nueva feature `equipos-coordinacion`**: gestión de equipos docentes desde coordinación — lista y filtro de asignaciones, alta masiva, clonado entre períodos, modificación de vigencia global, exportación, y vista "mis equipos" del docente autenticado.
- **Nueva feature `avisos`**: ABM completo de avisos del sistema con scope (global / materia / cohorte), roles destinatarios, severidad, ventana de visibilidad, acknowledgment y vista de lectores confirmados.
- **Nueva feature `tareas-coordinacion`**: workflow de tareas internas — panel del docente (mis tareas), asignación / reasignación, historial de comentarios, y vista de administración del coordinador (filtros, cambio de estado).
- **Nueva feature `coordinacion-academica`**: monitores transversales (F2.7, F2.9), vista de administración de encuentros (F6.5) y guardias (F6.6), y gestión completa de coloquios (F7.1–F7.5) desde coordinación.
- **Integración de navegación**: las nuevas rutas se registran en el shell de C-21 con lazy-load; el RBAC fino del JWT controla visibilidad.

## Capabilities

### New Capabilities

- `coordinacion-equipos-ui`: gestión frontend de equipos docentes — mis-equipos, asignaciones, alta masiva, clonar, vigencia, export (Épica 4, FL-03)
- `coordinacion-avisos-tareas-ui`: ABM de avisos con scope/ack (F3.5, FL-09) y workflow de tareas internas (Épica 8, FL-05)
- `coordinacion-academica-ui`: monitores transversales (F2.7, F2.9), encuentros admin (F6.5–F6.6) y coloquios (Épica 7)

### Modified Capabilities

_(ninguna — no cambian requisitos de specs existentes)_

## Impact

- **Frontend**: nuevas features bajo `frontend/src/features/equipos/`, `features/avisos/`, `features/tareas/`, `features/coordinacion-academica/`; registro de rutas en `AppRouter.tsx`
- **APIs consumidas**: `/api/equipos`, `/api/avisos`, `/api/tareas`, `/api/encuentros`, `/api/coloquios` — todo backend ya implementado en C-08, C-13, C-14, C-15, C-16, C-17
- **Dependencias**: C-21 (shell + auth), C-08, C-15, C-16; consumo indirecto de C-13, C-14, C-17
- **No breaking**: solo adición de rutas nuevas y hooks TanStack Query nuevos; cero cambios a specs de backend
