# Proposal: C-02 Core Models y Tenancy

## Intent

Establecer la infraestructura de aislamiento de datos (multi-tenancy) y seguridad (cifrado de PII) transversal a todo el sistema. Es crítico para asegurar que los datos no se crucen entre instituciones y que la información sensible cumpla con estándares de cifrado en reposo.

## Scope

### In Scope
- Implementación de modelo `Tenant` raíz.
- Mixins de SQLAlchemy (`UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin`, `TenantMixin`).
- `BaseRepository` con scope de tenant obligatorio (Row-Level Security lógico).
- Helper criptográfico `AES256Cipher` (Fernet) para PII.
- Migración inicial Alembic para la tabla `tenant`.
- Pruebas unitarias de aislamiento, cifrado y base repository.

### Out of Scope
- Autorización RBAC (Roles y Permisos). Se aborda en C-04.
- Endpoints HTTP y Routers para ABM de tenants (se manejan vía script o admin shell temporalmente, no hay endpoints C-02).
- Autenticación JWT y login (C-03).

## Capabilities

### New Capabilities
- `multi-tenancy`: Reglas de aislamiento de datos por institución (row-level security en capa lógica).
- `data-encryption`: Cifrado y descifrado de PII en la capa de datos.
- `soft-delete`: Mecanismo transversal de borrado lógico y auditoría de timestamps.

### Modified Capabilities
- None

## Approach

Implementar la base de SQLAlchemy 2.0 (async). Los mixins se añadirán a los modelos de dominio. El repositorio base interceptará las consultas, añadiendo la condición `tenant_id == current_tenant` forzosamente, salvo bypass explícito (e.g. tareas background globales). El cifrado utilizará `cryptography.fernet` con una clave master por entorno (`ENCRYPTION_KEY`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/` | New | `base.py`, `tenant.py` |
| `backend/app/repositories/` | New | `base.py` con `BaseRepository` |
| `backend/app/core/` | New | `security.py` (cifrado), `tenancy.py` (excepciones) |
| `backend/alembic/versions/` | New | Migración 001_tenant |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fuga de conexión async | Low | Testing estricto de lifespan y sessionmaker. |
| Olvido de scope tenant | Low | `BaseRepository` lanza error si `tenant_id` es nulo. Fail-closed. |
| Pérdida de `ENCRYPTION_KEY` | Low | Documentación clara sobre backup de variables de entorno. |

## Rollback Plan

- Revertir el commit (git revert).
- Hacer downgrade de la base de datos con `alembic downgrade base`.

## Dependencies

- C-01 (foundation-setup) completado y base de datos operativa.

## Success Criteria

- [ ] Un usuario asignado al Tenant A no puede recuperar datos del Tenant B desde el repositorio.
- [ ] Datos cifrados se guardan como string ininteligible en DB y se recuperan íntegros.
- [ ] Aplicar soft-delete a una entidad actualiza su `deleted_at` sin purgar físicamente la fila.
