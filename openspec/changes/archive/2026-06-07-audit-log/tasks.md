## 1. Migración 003_audit_log

- [x] 1.1 Crear migración Alembic `003_audit_log` con tabla `audit_log` (campos: id UUID PK, tenant_id UUID FK, fecha_hora timestamp TZ not null default now(), actor_id UUID FK → user, impersonado_id UUID FK → user nullable, materia_id UUID nullable, accion text not null, detalle JSONB, filas_afectadas integer, ip text, user_agent text)
- [x] 1.2 Agregar en `upgrade()` el trigger `audit_log_no_update_delete` que hace `RAISE EXCEPTION` en BEFORE UPDATE OR DELETE via `op.execute()`
- [x] 1.3 Verificar que `downgrade()` elimina la tabla con `DROP TABLE IF EXISTS audit_log CASCADE`

## 2. Modelo SQLAlchemy AuditLog

- [x] 2.1 Crear `backend/app/models/audit_log.py` con clase `AuditLog` usando mixins `TimestampMixin` y `TenantMixin` de C-02; campos: `actor_id`, `impersonado_id` (nullable), `materia_id` (nullable), `accion`, `detalle` (JSONB), `filas_afectadas` (nullable), `ip`, `user_agent`
- [x] 2.2 Exportar `AuditLog` desde `backend/app/models/__init__.py`

## 3. Repository AuditLogRepository

- [x] 3.1 Crear `backend/app/repositories/audit_log_repository.py` extendiendo `BaseRepository[AuditLog]`
- [x] 3.2 Override de `update()` que lanza `NotImplementedError("AuditLog es append-only — no se permite UPDATE")`
- [x] 3.3 Override de `delete()` que lanza `NotImplementedError("AuditLog es append-only — no se permite DELETE")`
- [x] 3.4 Método `create_entry(db, entry_data: dict) -> AuditLog` para insertar un registro (sin soft delete, sin update)

## 4. Helper de auditoría

- [x] 4.1 Crear `backend/app/core/audit.py` con constantes de códigos de acción: `CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, `COMUNICACION_ENVIAR`, `ASIGNACION_MODIFICAR`, `LIQUIDACION_CERRAR`, `IMPERSONACION_INICIAR`, `IMPERSONACION_FINALIZAR`
- [x] 4.2 Implementar función async `record_audit(db, current_user, action: str, request, detail: dict | None = None, rows_affected: int | None = None, materia_id: UUID | None = None) -> AuditLog` que extrae ip/user_agent del request, usa `current_user.id` como `actor_id` y `current_user.impersonado_id` como `impersonado_id`

## 5. Extender CurrentUser e identidad JWT

- [x] 5.1 Agregar campo `impersonado_id: uuid.UUID | None = None` al dataclass `CurrentUser` en `backend/app/core/dependencies.py`
- [x] 5.2 Modificar `get_current_user` para leer el claim `impersonado_id` del JWT y popularlo en `CurrentUser.impersonado_id` (None si el claim no existe)
- [x] 5.3 Verificar que `get_current_user` rechaza tokens con claim `impersonado_id` inválido (mal formado) con 401

## 6. Schemas de impersonación

- [x] 6.1 Agregar en `backend/app/schemas/auth.py`: `ImpersonateRequest(target_user_id: UUID)` y `ImpersonateResponse(impersonate_token: str, token_type: str = "bearer")`

## 7. Servicio y endpoints de impersonación

- [x] 7.1 En `backend/app/services/auth_service.py` implementar `impersonate(db, current_user, target_user_id: UUID) -> str`: verifica que `current_user` no tiene `impersonado_id` activo, busca `target_user` en el mismo tenant, crea JWT con TTL 60 min con `sub=current_user.id` + `impersonado_id=target_user.id`, registra `IMPERSONACION_INICIAR` en audit log
- [x] 7.2 En `auth_service.py` implementar `end_impersonation(current_user) -> None`: verifica que `current_user.impersonado_id` no es None, registra `IMPERSONACION_FINALIZAR` en audit log (el token se descarta del lado cliente)
- [x] 7.3 En `backend/app/api/v1/routers/auth.py` agregar `POST /impersonate` con guard `require_permission("impersonacion:usar")`, llama `auth_service.impersonate()`
- [x] 7.4 En el router auth agregar `POST /impersonate/end` con `get_current_user`, llama `auth_service.end_impersonation()`

## 8. Tests — append-only

- [x] 8.1 Test: `record_audit` crea registro con todos los campos correctos (actor_id, tenant_id, accion, ip, user_agent, filas_afectadas)
- [x] 8.2 Test: `record_audit` con `impersonado_id` poblado (current_user con impersonación activa) → `actor_id=actor_real.id`, `impersonado_id=target.id`
- [x] 8.3 Test: `record_audit` sin impersonación → `impersonado_id=None`
- [x] 8.4 Test: `AuditLogRepository.update()` lanza `NotImplementedError`
- [x] 8.5 Test: `AuditLogRepository.delete()` lanza `NotImplementedError`
- [x] 8.6 Test: trigger DB — ejecutar UPDATE directo via `execute()` en test → excepción levantada (tests en tests/repositories/test_audit_log_trigger.py, requiere PostgreSQL)

## 9. Tests — impersonación

- [x] 9.1 Test: `POST /auth/impersonate` con usuario sin permiso → 403
- [x] 9.2 Test: `POST /auth/impersonate` con target de otro tenant → 404
- [x] 9.3 Test: `POST /auth/impersonate` exitoso → 200 con token, audit log con `IMPERSONACION_INICIAR`
- [x] 9.4 Test: `POST /auth/impersonate` desde token con `impersonado_id` activo → 400
- [x] 9.5 Test: `POST /auth/impersonate/end` con token sin impersonación → 400
- [x] 9.6 Test: `POST /auth/impersonate/end` exitoso → 200, audit log con `IMPERSONACION_FINALIZAR`
- [x] 9.7 Test: `get_current_user` con JWT que tiene `impersonado_id` → `CurrentUser.impersonado_id` poblado
- [x] 9.8 Test: `get_current_user` con JWT normal → `CurrentUser.impersonado_id = None`

## 10. Tests — tenant isolation

- [x] 10.1 Test: acción auditada por tenant A no aparece en consulta de tenant B (tenant isolation del repository)
