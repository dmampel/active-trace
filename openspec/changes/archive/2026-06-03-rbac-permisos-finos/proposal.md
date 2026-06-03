## Why

C-03 dejó la identidad resuelta (quién es el usuario y a qué tenant pertenece), pero sin ningún mecanismo que controle qué puede hacer. Todos los endpoints protegidos quedan iguales de accesibles para cualquier usuario autenticado hasta que RBAC esté activo. C-04 cierra esa brecha: agrega el catálogo de roles y permisos finos, la resolución server-side y el guard declarativo `require_permission`, desbloqueando el GATE 4 (fork hacia C-05, C-06 y C-21).

## What Changes

- Nuevas tablas: `rol`, `permiso`, `rol_permiso` (catálogo administrable, datos — no hardcode).
- Seed de la matriz canónica: roles ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS con sus permisos `modulo:accion` según `03_actores_y_roles.md §3.3`.
- Tabla `user_rol` (asignación usuario↔rol dentro del tenant, con vigencia `desde`/`hasta`).
- Función de resolución de permisos efectivos server-side: unión de los roles vigentes del usuario, acotada por `tenant_id`.
- Dependency/guard `require_permission("modulo:accion")` para FastAPI: fail-closed (sin permiso explícito → 403).
- JWT access token poblado con la lista de roles vigentes (actualmente `roles: []`).
- Migración Alembic 003: `rol`, `permiso`, `rol_permiso`, `user_rol` + seed de la matriz base.
- `app/core/permissions.py` implementado (actualmente es un stub reservado para C-04).

## Capabilities

### New Capabilities
- `rbac`: Catálogo administrable de roles y permisos finos (`modulo:accion`), resolución de permisos efectivos server-side y guard declarativo `require_permission` para endpoints FastAPI. Fail-closed: sin permiso explícito → 403.

### Modified Capabilities
- `user-auth`: El JWT access token ahora incluye los roles vigentes del usuario en el claim `roles` (antes siempre `[]`). No cambia el contrato externo de login/refresh, solo el contenido del token.

## Impact

- **Nuevos modelos**: `Rol`, `Permiso`, `RolPermiso`, `UserRol` en `backend/app/models/rbac.py`.
- **Nuevo repositorio**: `RbacRepository` en `backend/app/repositories/rbac_repository.py`.
- **`app/core/permissions.py`**: implementación completa de `require_permission`, `get_effective_permissions`, `has_permission`.
- **`app/core/dependencies.py`**: `get_current_user` actualizado para cargar roles desde DB y poblar el JWT.
- **`app/services/auth_service.py`**: `_build_token_response` pobla `roles` con roles vigentes del usuario.
- **Migración Alembic 003**: tablas + seed de la matriz base.
- **Tests nuevos**: `tests/core/test_permissions.py`, `tests/repositories/test_rbac_repository.py`.
