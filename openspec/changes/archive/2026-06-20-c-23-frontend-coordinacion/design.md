## Context

El shell SPA (C-21) está operativo con `AuthContext`, `AppRouter`, guard de permisos y layout principal. C-22 completó las features del PROFESOR (importacion, analisis, comunicacion). El backend de coordinación está completo: equipos (C-08), encuentros (C-13), coloquios (C-14), avisos (C-15), tareas (C-16).

C-23 es exclusivamente frontend: construye las pantallas del COORDINADOR y ADMIN sobre el shell existente, sin tocar backend, modelos ni migraciones.

## Goals / Non-Goals

**Goals:**
- Feature `equipos`: mis-equipos, asignaciones con filtros, alta masiva, clonar período, modificación de vigencia global, exportación (F4.2–F4.7, FL-03 parcial).
- Feature `avisos`: ABM completo con scope/roles/severidad/vigencia/ack, vista de confirmaciones (F3.5, FL-09).
- Feature `tareas`: panel del docente (mis tareas + comentarios), administración del coordinador con filtros y cambio de estado (F8.1–F8.3, FL-05).
- Feature `coordinacion-academica`: monitor general (F2.7), monitor con rango de fechas (F2.9), vista admin de encuentros + guardias (F6.5–F6.6), gestión completa de coloquios (F7.1–F7.5), cola de aprobación de comunicaciones (F3.3).
- Tests de componente e integración con mocks de API para todos los flujos principales.

**Non-Goals:**
- Cualquier cambio en backend, modelos o migraciones de base de datos.
- Liquidaciones, facturas, estructura académica (carreras/cohortes/programas) → C-24.
- Panel de auditoría → C-24.
- Soporte mobile-first / PWA.

## Decisions

### D1 — Estructura de features

Cuatro features bajo `frontend/src/features/`:

```
frontend/src/features/
├── equipos/              ← F4.2–F4.7, FL-03
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── pages/
├── avisos/               ← F3.5, FL-09
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── pages/
├── tareas/               ← F8.1–F8.3, FL-05
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── pages/
└── coordinacion/         ← F2.7, F2.9, F3.3, F6.5–F6.6, F7.1–F7.5
    ├── components/
    ├── hooks/
    ├── services/
    ├── types/
    └── pages/
```

**Alternativa descartada**: un único módulo `coordinacion/` con sub-carpetas para todo. Se descartó porque `equipos`, `avisos` y `tareas` tienen lógica y endpoints bien diferenciados y pueden evolucionar independientemente.

### D2 — Rutas bajo `/coordinacion/` y `/mis-*`

Las rutas se añaden al router existente (AppRouter.tsx) con lazy-load. El guard de permisos ya existente bloquea acceso a roles sin la permission requerida.

```
/equipos                        → EquiposPage (mis-equipos + admin)
/equipos/masiva                 → AsignacionMasivaPage
/equipos/clonar                 → ClonarEquipoPage

/avisos                         → AvisosPage (ABM + lista activos)
/avisos/nuevo                   → NuevoAvisoPage
/avisos/:id/editar              → EditarAvisoPage
/avisos/:id/confirmaciones      → ConfirmacionesAvisoPage

/tareas                         → MisTareasPage  (docente)
/coordinacion/tareas            → AdminTareasPage (coordinador)

/coordinacion/monitores         → MonitorGeneralPage (F2.7)
/coordinacion/monitores/seguimiento → MonitorSeguimientoPage (F2.9)
/coordinacion/encuentros        → EncuentrosAdminPage (F6.5–F6.6)
/coordinacion/coloquios         → ColoquiosPage (F7.1–F7.5)
/coordinacion/comunicaciones/aprobacion → AprobacionComunicacionesPage (F3.3)
```

### D3 — Tabla de datos con filtros via TanStack Query

Los listados de equipos, tareas y monitores usan parámetros de filtro como `queryKey` de TanStack Query. Cambiar un filtro invalida el cache de esa query sin afectar otras. Los filtros se sincronizan con search-params de la URL para que sean compartibles y sobrevivan reload.

**Alternativa descartada**: estado local en `useState` para filtros. Se descartó porque impide compartir URLs filtradas y complica el back-button del navegador.

### D4 — Tabla de mis-equipos con tabs de vista

`EquiposPage` tiene tabs (Mis asignaciones / Actividad / Comunicaciones del equipo) siguiendo F4.2. Cada tab es una query independiente lazy-iniciada cuando el tab se activa por primera vez. Tabs implementados con estado local `activeTab` + renderizado condicional, no rutas anidadas — la página es suficientemente compacta.

### D5 — Wizard de clonar equipo como stepper local

El flujo de clonado (FL-03 paso 2) usa un stepper de 3 pasos: selección origen → selección destino → confirmación. El estado vive en `useReducer` local al componente `ClonarEquipoPage`. Solo el paso 3 dispara la mutación al backend (`POST /api/equipos/clonar`).

### D6 — Editor de aviso con campo `scope` reactivo

El formulario de aviso (React Hook Form + Zod) muestra u oculta los selectores de materia y cohorte según el valor del campo `scope` (global / materia / cohorte). La validación Zod usa `.superRefine()` para exigir `materiaId` cuando `scope === 'materia'` y además `cohorteId` cuando `scope === 'cohorte'`.

### D7 — Coloquios: doble vista (lista convocatorias + detalle)

`ColoquiosPage` lista convocatorias con métricas (F7.4). Al hacer click en una convocatoria, `ColoquioDetallePage` muestra agenda, reservas activas, importación de padrón y registro académico de resultados. La navegación usa `/coordinacion/coloquios/:convocatoriaId`.

### D8 — Cola de aprobación de comunicaciones via polling

`AprobacionComunicacionesPage` lista mensajes en estado Pendiente del tenant. Usa `refetchInterval: 5000` mientras haya mensajes en cola. Las acciones aprobar/cancelar (por mensaje o por lote) son mutaciones POST que invalidan la query al completarse.

## Risks / Trade-offs

- **[Risk] Listados grandes en monitores transversales (F2.7)** → El backend ya pagina; el frontend usa cursor/page params en la URL. Mitigation: virtualización de tabla con `@tanstack/react-virtual` si filas > 200 por página.
- **[Risk] Stepper de clonar equipo con errores 409** → Si el destino ya tiene asignaciones, el backend retorna 409. Mitigation: manejar explícitamente en el paso 3 con mensaje descriptivo y opción de reintentar con otro destino.
- **[Risk] Formulario de aviso con validación condicional compleja** → `.superRefine()` puede producir errores de tipado en inferencia Zod. Mitigation: schema base + `.and()` discriminado por scope para mejor tipado.

## Migration Plan

Sin migración de datos ni backend. Las rutas nuevas se registran con lazy-load en AppRouter.tsx; el guard existente maneja el 403 si el usuario no tiene el permiso requerido. El deploy es incremental — las pantallas sin permiso simplemente no se renderizan.
