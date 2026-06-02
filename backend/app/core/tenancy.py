"""RESERVADO para C-02 (core-models-y-tenancy).

Este módulo implementará:
- Resolución del tenant_id desde la sesión JWT verificada
- Aislamiento row-level: todo query filtra por tenant_id por defecto (ADR-002)
- Un query sin scope de tenant es un bug que falla en code review

REGLA: la identidad del tenant SIEMPRE viene del JWT verificado.
NUNCA desde parámetros de URL, body o headers de la petición.
"""

# Implementar en C-02: get_current_tenant(current_user) -> Tenant
# Implementar en C-02: TenantScopedRepository (base con filtro tenant_id implícito)
