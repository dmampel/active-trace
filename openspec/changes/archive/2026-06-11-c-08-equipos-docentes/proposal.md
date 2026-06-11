## Why

Con C-07 el sistema puede gestionar usuarios individuales y asignaciones unitarias, pero no hay operaciones colectivas sobre equipos: no existe forma de asignar docentes en bloque, clonar un equipo entre cohortes, ajustar vigencias masivamente ni exportar el plantel. Al inicio de cada período académico esto obliga a reconfigurar todo desde cero, uno por uno.

## What Changes

- **Vista "mis equipos"**: el docente autenticado puede ver todas las comisiones y materias en las que está asignado, con filtros por estado, materia, rol, carrera y cohorte (F4.2).
- **Asignación masiva**: selección múltiple de docentes + destino (materia × carrera × cohorte × rol) con vigencia en bloque; búsqueda asistida por autocompletado del servidor (F4.4, RN-30).
- **Clonar equipo**: duplica todas las asignaciones de un equipo origen hacia un destino diferente, para migración entre cuatrimestres (F4.5, RN-12).
- **Vigencia general del equipo**: actualiza `vigencia_desde` / `vigencia_hasta` de todas las asignaciones de un equipo en una sola operación (F4.6).
- **Exportar equipo**: descarga CSV/XLSX con el detalle completo del equipo docente activo (F4.7).
- **Consulta de asignaciones individuales**: vista de coordinador/admin con filtros cruzados por materia, carrera, cohorte, usuario y rol (F4.3).

## Capabilities

### New Capabilities

- `equipos-docentes`: endpoints y lógica de negocio para las operaciones colectivas sobre equipos: mis-equipos (vista propia del docente), asignación masiva, clonar, modificar vigencia general y exportar.

### Modified Capabilities

- `asignaciones`: los endpoints existentes de lectura de asignaciones individuales reciben filtros adicionales (carrera, cohorte, materia, rol) para cubrir la vista de coordinador/admin (F4.3). No hay cambios de esquema — solo nuevos query params.

## Impact

- **Backend**: nuevos endpoints en `routers/equipos.py`; servicio `EquipoService` con las operaciones masivas; repositorio extendido `AsignacionRepository` (métodos bulk insert, clone, bulk update vigencia, export query).
- **Modelos**: sin cambios de esquema — C-07 ya creó `Asignacion`. Solo se añaden índices de apoyo si el plan de queries los requiere.
- **Migraciones**: ninguna obligatoria; índices opcionales en una migración separada si se detectan en diseño.
- **Permisos RBAC**: `equipos:read_own`, `equipos:manage`, `equipos:export` — declarados en el catálogo de permisos existente.
- **Testing**: suite de integración sobre DB real (docker activia-test, puerto 5433).
