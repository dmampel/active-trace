## Why

Los equipos docentes y de coordinación necesitan un canal asincrónico para delegar, escalar y dar seguimiento a acciones concretas dentro del tenant. Sin un módulo de tareas internas, el seguimiento ocurre fuera del sistema (WhatsApp, email), perdiéndose trazabilidad y auditoría. C-07 (usuarios y asignaciones) ya está completo, lo que provee la infraestructura de roles necesaria para asignar responsables.

## What Changes

- Nuevos modelos `Tarea` y `ComentarioTarea` con persistencia multi-tenant (tabla `tarea`, tabla `comentario_tarea`, migración `016`).
- Estado de tarea con máquina de estados: `Pendiente → En progreso → Resuelta | Cancelada`.
- Endpoints REST `POST /api/tareas`, `GET /api/tareas/mis-tareas`, `PATCH /api/tareas/{id}/estado`, `POST /api/tareas/{id}/comentarios`, `GET /api/tareas` (admin con filtros).
- Guard `tareas:gestionar` requerido en todos los endpoints; COORDINADOR/ADMIN acceden a la vista global; TUTOR/PROFESOR ven solo sus tareas.
- Delegación de tarea con trazabilidad `asignado_por` / `asignado_a` (F8.2).
- Hilo de comentarios por tarea (F8.3).
- Módulo dimensionado para alto throughput: cientos de tareas simultáneas durante período activo.

## Capabilities

### New Capabilities

- `tareas-internas`: Gestión completa del ciclo de vida de tareas internas — alta, asignación/delegación, transiciones de estado, hilo de comentarios y administración global con filtros.

### Modified Capabilities

*(ninguna — no hay cambios en specs existentes)*

## Impact

- **Nuevas tablas**: `tarea`, `comentario_tarea` (migración Alembic `016_tareas_internas`).
- **Nuevos módulos**: `backend/app/models/tarea.py`, `backend/app/repositories/tarea_repository.py`, `backend/app/services/tarea_service.py`, `backend/app/routers/tareas.py`, `backend/app/schemas/tarea.py`.
- **Permiso nuevo**: `tareas:gestionar` — declarado en la tabla de permisos / RBAC (C-04).
- **Sin dependencias externas** más allá de C-07 (usuarios ya disponibles).
- **Tests**: alta + asignación, delegación con trazabilidad, transiciones de estado, comentarios en hilo, filtros de admin, row-level multi-tenant.
