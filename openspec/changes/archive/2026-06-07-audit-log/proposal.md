## Why

Sin un log de auditoría append-only, no hay trazabilidad de acciones críticas (importaciones, comunicaciones, impersonaciones). Es el requisito de cumplimiento más básico de la plataforma y GATE 4 lo habilita: con RBAC listo, ya sabemos quién hace qué y podemos registrarlo correctamente.

## What Changes

- Modelo `AuditLog` (E-AUD) con restricción append-only a nivel aplicación y base de datos.
- Helper/decorator `audit_action` para registrar acciones significativas con código estandarizado (`CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, etc.).
- Soporte de **impersonación**: permiso `impersonacion:usar`, endpoint para iniciar/finalizar sesión de impersonación, atribución de acciones al actor real con `actor_id` + `impersonado_id`.
- Dependencia de `get_current_user` para inyectar identidad y `impersonado_id` en cada registro.
- Migración `003_audit_log` con constraint `CHECK` que previene UPDATE/DELETE a nivel DB.
- Tests: append-only enforced, atribución bajo impersonación, registro de acción con código + filas afectadas, multi-tenant isolation.

## Capabilities

### New Capabilities

- `audit-log`: Modelo AuditLog append-only, helper de registro, soporte de impersonación (iniciar/finalizar sesión), catálogo inicial de códigos de acción.

### Modified Capabilities

- `user-auth`: Agrega endpoints de impersonación (`POST /auth/impersonate`, `POST /auth/impersonate/end`) y `impersonado_id` en el JWT payload cuando hay sesión activa de impersonación.

## Impact

- **Nuevo**: `backend/app/models/audit_log.py`, `backend/app/repositories/audit_log_repository.py`, `backend/app/core/audit.py` (helper), `backend/alembic/versions/003_audit_log.py`.
- **Modificado**: `backend/app/api/v1/routers/auth.py` (endpoints de impersonación), `backend/app/schemas/auth.py` (campo `impersonado_id` en token), `backend/app/core/dependencies.py` (inyectar `impersonado_id` desde JWT).
- **API**: dos endpoints nuevos en `/auth` (CRÍTICO — governance).
- **Dependencias**: ninguna nueva librería; usa SQLAlchemy async existente.
