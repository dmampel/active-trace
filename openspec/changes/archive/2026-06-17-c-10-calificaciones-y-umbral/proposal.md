
## Why

Una vez que el padrón está cargado (C-09), el siguiente paso del camino crítico es traer las calificaciones reales del LMS para poder analizar quién está atrasado y comunicarse con ellos (C-11/C-12). Hoy el sistema no tiene dónde guardar la nota de un alumno por actividad, ni un criterio de aprobación configurable por docente. C-10 introduce ese núcleo: importar calificaciones desde el archivo del LMS, derivar de forma determinística si cada nota es aprobatoria, detectar trabajos entregados sin corregir, y dejar que cada docente configure su propio umbral sin pisar los datos de otros.

## What Changes

- Nuevo modelo **Calificacion**: nota numérica y/o textual de un alumno (`entrada_padron_id`) en una `actividad`; `aprobado` es **derivado** (no se persiste como verdad independiente, se recalcula a partir del umbral vigente); `origen` enum (`Importado` | `Manual`); `importado_at`.
- Nuevo modelo **UmbralMateria**: `umbral_pct` (defecto 60) y `valores_aprobatorios` (lista de valores textuales aprobatorios) por **asignación docente** (`asignacion_id`), scope-isolated por docente.
- **F1.1 — Importar calificaciones desde archivo del LMS**: detecta columnas de nota numérica (RN-01: encabezado termina en `(Real)`) y valores textuales (RN-02), genera una **vista previa** de actividades y alumnos detectados, y deja que el usuario **seleccione qué actividades** incluir antes de persistir.
- **F1.2 — Importar reporte de finalización**: cruza el reporte con las calificaciones para detectar TPs entregados sin nota (RN-07), agrupando **solo** actividades de escala textual (RN-08).
- **F2.1 — Configurar umbral por materia**: por asignación docente (RN-03, defecto 60%), no afecta los datos de otros docentes.
- **Derivación de `aprobado`** como **función pura** de dominio (no en modelo ni repositorio): numérica vs umbral, textual vs conjunto aprobatorio, con precedencia definida cuando coexisten.
- Acción de auditoría `CALIFICACIONES_IMPORTAR` en cada importación (RN-23/RN-24).
- Nuevos permisos RBAC `calificaciones:importar` y `calificaciones:leer`, sembrados en la migración.
- Migración Alembic `009_calificaciones_tables` (sigue a `008_padron_tables`): tablas `calificacion` y `umbral_materia` + permisos.

## Capabilities

### New Capabilities
- `calificaciones`: importación de calificaciones desde archivo del LMS con vista previa y selección de actividades, importación del reporte de finalización (entregas sin corregir), configuración de umbral por asignación docente, y la derivación determinística del estado `aprobado`.

### Modified Capabilities
<!-- Ninguna. C-10 no modifica requisitos de specs existentes; consume padron-ingesta como dependencia (FK a entrada_padron) sin cambiar su comportamiento. -->

## Impact

- **Modelos nuevos**: `backend/app/models/calificacion.py` (`Calificacion`, `UmbralMateria`, enum `OrigenCalificacion`).
- **Migración**: `backend/alembic/versions/009_calificaciones_tables.py` (down_revision `a8b9c0d1e2f3`).
- **Dominio puro**: `backend/app/domain/aprobado.py` (función `derivar_aprobado`) — regla de negocio núcleo, cobertura ≥90%.
- **Repositorios**: `backend/app/repositories/calificacion_repository.py`, `umbral_repository.py` (filtran por `tenant_id` por defecto).
- **Servicios**: `backend/app/services/calificacion_service.py` (parser LMS, preview, persistencia, cruce de finalización, audit), `umbral_service.py`.
- **Schemas**: `backend/app/schemas/calificacion.py` (todos con `extra='forbid'`).
- **Router**: `backend/app/api/v1/routers/calificaciones.py` (RBAC fail-closed, identidad desde JWT, scope tenant).
- **RBAC**: permisos `calificaciones:importar` (PROFESOR, COORDINADOR) y `calificaciones:leer` (PROFESOR, TUTOR, COORDINADOR, ADMIN) sembrados en la migración.
- **Dependencias**: consume `entrada_padron` (C-09) y `asignacion` (C-06/usuarios) como targets de FK. No rompe nada existente.
- **PA-01 abierto**: el ERD referencia `InstanciaDictado`; C-10 sigue la convención implementada en C-09 (`materia_id` UUID indexado, no FK dura) hasta resolver PA-01.
