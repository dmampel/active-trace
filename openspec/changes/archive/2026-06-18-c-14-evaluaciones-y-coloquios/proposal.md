## Why

El sistema necesita gestionar instancias de evaluación formal (coloquios, parciales, recuperatorios) con convocatoria, cupos por turno y reserva de turno por el alumno. Actualmente no existe ningún módulo que cubra este flujo (FL-07), bloqueando la operativa académica de cierre de período.

## What Changes

- Nuevo modelo `Evaluacion` — convocatoria de coloquio con materia, cohorte, instancia, días disponibles y cupos por turno.
- Nuevo modelo `ReservaEvaluacion` — reserva de turno por ALUMNO con estado Activa/Cancelada y control de cupo atómico.
- Nuevo modelo `ResultadoEvaluacion` — registro académico de nota final por alumno y evaluación.
- Nuevo modelo `FechaAcademica` — calendarización de instancias evaluativas (parciales, TPs, coloquios) por materia × cohorte.
- API `/api/coloquios/*` — CRUD de convocatorias (COORDINADOR/ADMIN) y reserva de turno (ALUMNO).
- API `/api/fechas-academicas/*` — CRUD de fechas de evaluación (COORDINADOR/ADMIN).
- Importación de alumnos habilitados a una convocatoria (F7.2).
- Panel de métricas de coloquios (F7.1): convocados, reservas activas, cupos libres, notas registradas.
- Admin global de coloquios (F7.5): gestión de convocatorias, registro consolidado de resultados, agenda de reservas.
- Migraciones Alembic para `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion`, `fecha_academica`.

## Capabilities

### New Capabilities

- `evaluaciones-y-coloquios`: Gestión completa del ciclo de coloquio — convocatorias con cupos, reserva de turno por alumno, seguimiento de métricas, registro de resultados y calendarización de fechas académicas (F7.1–F7.5, F5.4, FL-07).

### Modified Capabilities

<!-- Ninguna: toda la funcionalidad es nueva. -->

## Impact

- **Modelos**: `backend/app/models/evaluacion.py` (Evaluacion, ReservaEvaluacion, ResultadoEvaluacion, FechaAcademica).
- **Schemas**: `backend/app/schemas/evaluacion.py` — DTOs de request/response para todos los recursos.
- **Repositories**: `backend/app/repositories/evaluacion_repository.py`, `backend/app/repositories/fecha_academica_repository.py`.
- **Services**: `backend/app/services/evaluacion_service.py`, `backend/app/services/fecha_academica_service.py`.
- **Routers**: `backend/app/api/v1/routers/coloquios.py`, `backend/app/api/v1/routers/fechas_academicas.py`.
- **Migraciones**: una migración Alembic con las 4 tablas nuevas.
- **Dependencias**: `C-07` (usuarios, instancias dictado). Sin bloqueadores de preguntas abiertas activas para este scope.
- **Permisos nuevos**: `coloquios:gestionar`, `coloquios:ver`, `coloquios:reservar`, `fechas_academicas:gestionar`.
