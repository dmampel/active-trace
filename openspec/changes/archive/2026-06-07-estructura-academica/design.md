## Context

El backend ya tiene C-01→C-05 completos: foundation, tenancy, auth JWT+2FA, RBAC con `require_permission`, audit log. Existen mixins `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin`, `TenantMixin` en `app/models/base.py` y un `BaseRepository` con tenant isolation en `app/repositories/base.py`. Las migraciones llegan hasta `004_audit_log`. Este change agrega el catálogo académico raíz que desbloquea todos los changes posteriores.

## Goals / Non-Goals

**Goals:**
- Crear modelos SQLAlchemy para `Carrera`, `Cohorte`, `Materia`, `InstanciaDictado` usando los mixins existentes.
- ABM REST completo (CRUD + soft delete) para cada entidad.
- RBAC fino: cuatro permisos `estructura:leer|crear|editar|eliminar` con matrix estándar.
- Migración Alembic `005_estructura_academica` con índices y constraints únicos.
- Auditoría de operaciones write (crear, editar, eliminar).
- Tests con Strict TDD: ≥80% cobertura, ≥90% reglas de negocio.

**Non-Goals:**
- No incluye asignaciones de docentes a materias/cohortes (C-07).
- No incluye padrón ni calificaciones (C-09, C-10).
- No incluye frontend (C-21+).
- No implementa relaciones ORM hacia entidades de changes futuros.

## Decisions

### D1 — Un solo archivo de modelos por dominio
`app/models/estructura.py` contiene las 4 entidades. Alternativa (un archivo por entidad) agregaría complejidad innecesaria dado el tamaño de cada modelo. Si alguna entidad crece mucho en C-07+ se extrae entonces.

### D2 — Repositorios separados por entidad
`CarreraRepository`, `CohorteRepository`, `MateriaRepository`, `InstanciaDictadoRepository` heredan de `BaseRepository`. Alternativa (un `EstructuraRepository` monolítico) viola el principio de responsabilidad única. Un repo por entidad es consistente con el patrón de `UserRepository` y `RbacRepository`.

### D3 — Servicio único `EstructuraService`
Toda la lógica de negocio (validaciones cross-entity, lanzar AuditLog, gestionar transacciones) vive en `app/services/estructura_service.py`. Alternativa (servicios separados) agregaría boilerplate sin beneficio en este stage; si escalan se separan en C-07+.

### D4 — Router único con prefijo `/api/v1/estructura`
Sub-rutas: `/carreras`, `/cohortes`, `/materias`, `/instancias`. Un solo router importado en `main.py`. Consistente con el patrón existente de `/auth` y `/admin/rbac`.

### D5 — Permisos RBAC `estructura:*`
Se registran 4 permisos en seed (o migración de datos): `estructura:leer`, `estructura:crear`, `estructura:editar`, `estructura:eliminar`. Roles predeterminados: ADMIN tiene los 4; COORDINADOR tiene `leer|crear|editar`; PROFESOR/TUTOR tienen solo `leer`. Se inyectan con `require_permission(...)` igual que el resto del sistema.

### D6 — InstanciaDictado como entidad explícita (no view)
Después de cerrar PA-01: `Materia` es el catálogo curricular (plan) y `InstanciaDictado` es la oferta concreta (materia + cohorte + periodo). Las entidades downstream (padrón, calificaciones, encuentros) referirán a `instancia_id`. Constraint único DB: `(tenant_id, materia_id, cohorte_id, periodo)`.

### D7 — Soft delete via `deleted_at` (existente en mixins)
Consistente con el resto del sistema. Los repositorios filtran `deleted_at IS NULL` por defecto. Hard delete no permitido.

### D8 — Migración `005_estructura_academica`
Una sola migración Alembic que crea las 4 tablas. Índices: `(tenant_id)` en cada tabla + `(tenant_id, codigo)` en Carrera y Materia + `(tenant_id, carrera_id, nombre)` en Cohorte + `(tenant_id, materia_id, cohorte_id, periodo)` en InstanciaDictado.

## Risks / Trade-offs

- **Acoplamiento downstream**: InstanciaDictado establece una FK que todos los changes posteriores usarán. Un cambio de schema en ella requeriría migraciones en cascada. Mitigación: diseño deliberado y revisado antes de aplicar.
- **Nombre de migración colisionante**: si se crearon migraciones en paralelo (C-05 es 004), hay que verificar el orden de `down_revision` en Alembic. Mitigación: verificar `alembic heads` antes de correr la migración.
- **Permisos en seed vs. migración**: registrar permisos en la migración de datos los acopla al ciclo de schema. Alternativa: script de seed separado. Decisión: migración de datos en la misma `005` para mantener el sistema reproducible desde cero.

## Migration Plan

1. Aplicar `005_estructura_academica` (crea tablas, índices, constraints, permisos en tabla `permission`).
2. Seed de permisos → roles (si el tenant ya tiene roles creados, se actualiza la tabla `role_permission`).
3. No hay rollback destructivo: `downgrade()` dropea las 4 tablas solo en ambientes de desarrollo (sin datos).
