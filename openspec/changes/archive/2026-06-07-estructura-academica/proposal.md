## Why

El sistema necesita las entidades raíz del dominio académico para poder operar: sin Carrera, Cohorte, Materia e InstanciaDictado no hay contexto donde asignar docentes, cargar padrón, registrar calificaciones ni generar liquidaciones. C-06 establece el catálogo académico completo del tenant con ABM completo y restricción de multi-tenancy, desbloqueando GATE 5 del roadmap.

## What Changes

- Nuevas entidades: `Carrera`, `Cohorte`, `Materia`, `InstanciaDictado` con sus tablas Alembic y modelos SQLAlchemy.
- ABM REST completo para cada entidad (CRUD + soft delete) bajo `/api/v1/`.
- Permisos RBAC `estructura:leer`, `estructura:crear`, `estructura:editar`, `estructura:eliminar` con matriz de roles.
- Migración Alembic `0002_estructura_academica` con índices de tenant y constraints únicos.
- Validación de `InstanciaDictado`: constraint único `(tenant_id, materia_id, cohorte_id, periodo)`.
- Regla: cohorte pertenece a exactamente una carrera (`carrera_id` NOT NULL).

## Capabilities

### New Capabilities

- `estructura-academica`: ABM de Carrera, Cohorte, Materia e InstanciaDictado con multi-tenancy, soft delete, permisos RBAC finos y migración Alembic.

### Modified Capabilities

_(ninguna — es todo nuevo)_

## Impact

- **Backend**: nuevos módulos `app/models/estructura.py`, `app/repositories/estructura.py`, `app/services/estructura.py`, `app/api/v1/routers/estructura.py`.
- **Alembic**: nueva migración `0002_estructura_academica.py`.
- **RBAC**: cuatro nuevos permisos `estructura:*` registrados en la tabla de permisos.
- **Downstream**: C-07 (usuarios-y-asignaciones), C-09 (padron), C-10 (calificaciones) y la mayoría de changes posteriores dependen de estas entidades.
