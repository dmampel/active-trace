"""RESERVADO para C-04 (rbac-permisos-finos).

Este módulo implementará:
- Catálogo administrable de permisos (modulo:accion)
- Resolución de permisos efectivos por usuario + roles + tenant
- Guard require_permission(modulo:accion) para endpoints
- Fail-closed: sin permiso explícito → 403

NO agregar lógica en este archivo hasta C-04.
"""

# Implementar en C-04: has_permission(user, permission) -> bool
# Implementar en C-04: get_effective_permissions(user, tenant) -> set[str]
# Implementar en C-04: require_permission(permission: str) -> Depends(...)
