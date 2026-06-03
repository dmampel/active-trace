## 1. Modelos RBAC

- [x] 1.1 Crear `backend/app/models/rbac.py` con modelos `Rol`, `Permiso`, `RolPermiso`, `UserRol` (UUIDMixin, TimestampMixin; `UserRol` tiene `desde DATE NOT NULL`, `hasta DATE NULLABLE`)
- [x] 1.2 Registrar los nuevos modelos en `backend/app/models/__init__.py`
- [x] 1.3 Test: instanciar modelos en SQLite in-memory y verificar campos `desde`/`hasta` en `UserRol`


## 2. Migración Alembic 003

- [x] 2.1 Generar migración 003 (`003_rbac_tables`) con DDL para `rol`, `permiso`, `rol_permiso`, `user_rol`
- [x] 2.2 Agregar seed en la migración: 7 roles canónicos (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS)
- [x] 2.3 Agregar seed: permisos `modulo:accion` de la matriz canónica (`03_actores_y_roles.md §3.3`)
- [x] 2.4 Agregar seed: asociaciones `rol_permiso` de la matriz canónica (NEXO sin permisos — PA-25 pendiente)
- [x] 2.5 Test: verificar que el archivo de migración es válido (`alembic check` o revisión manual de sintaxis)

## 3. Repositorio RBAC

- [x] 3.1 Crear `backend/app/repositories/rbac_repository.py` con `RbacRepository` (sync, misma convención que `UserRepository`)
- [x] 3.2 Implementar `get_user_roles(session, user_id, tenant_id) → list[str]`: roles vigentes del usuario (filtra por vigencia y tenant)
- [x] 3.3 Implementar `get_effective_permissions(session, user_id, tenant_id) → set[str]`: unión de permisos de los roles vigentes
- [x] 3.4 Test RED: `test_user_with_no_roles_has_no_permissions` → `get_effective_permissions` retorna set vacío
- [x] 3.5 Test GREEN: implementar y pasar el test
- [x] 3.6 Test TRIANGULATE: `test_admin_role_has_estructura_gestionar`, `test_role_union_merges_permissions`, `test_expired_role_not_included`

## 4. Permissions module (`app/core/permissions.py`)

- [x] 4.1 Implementar `has_permission(effective: set[str], permission: str) → bool`
- [x] 4.2 Implementar `require_permission(permission: str)` como FastAPI dependency factory: llama `get_current_user` + `get_sync_db` + `RbacRepository.get_effective_permissions` y lanza 403 si no tiene el permiso
- [x] 4.3 Test RED: `test_require_permission_returns_403_when_user_lacks_permission`
- [x] 4.4 Test GREEN: implementar y pasar el test
- [x] 4.5 Test TRIANGULATE: `test_require_permission_passes_when_user_has_permission`, `test_require_permission_fail_closed_unknown_permission`

## 5. Integración con JWT (poblar claim `roles`)

- [x] 5.1 Modificar `backend/app/api/v1/auth.py` (endpoint `POST /login`):
  - Inyectar `session` y obtener los roles usando `RbacRepository.get_user_roles(session, user.id, user.tenant_id)`
  - Agregar `roles` al payload al generar `access_token` y `refresh_token`
- [x] 5.2 Test RED: `test_login_includes_roles_in_jwt` (hacer un request a `/login`, decodificar token, asertar `roles`)
- [x] 5.3 Test GREEN: implementar y pasar
- [x] 5.4 Test TRIANGULATE: `test_login_user_with_no_roles_has_empty_list_in_jwt` — el refresh re-resuelve roles vigentes

## 6. Endpoint de prueba RBAC

- [x] 6.1 Habilitar los endpoints `POST /api/v1/auth/2fa/enroll` y `POST /api/v1/auth/2fa/enroll/confirm` usando `get_current_user` (estaban en 501 por ausencia de guard — ahora disponibles)
- [x] 6.2 Test de integración: `test_totp_enroll_requires_authentication` → sin JWT → 401
