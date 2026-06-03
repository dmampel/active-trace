## Context

C-03 dejó `get_current_user` funcional con `CurrentUser(id, tenant_id, roles)`, pero `roles` siempre es `[]` y `app/core/permissions.py` es un stub vacío. No existe ningún mecanismo que controle qué puede hacer un usuario autenticado.

C-04 implementa el catálogo administrable de roles y permisos, la resolución server-side y el guard declarativo. Es el gate de seguridad que habilita el GATE 4 del roadmap.

## Goals / Non-Goals

**Goals:**
- Catálogo administrable (datos): tablas `rol`, `permiso`, `rol_permiso`, `user_rol`.
- Resolución de permisos efectivos server-side en cada request (unión de roles vigentes del usuario, acotada por tenant).
- Guard `require_permission("modulo:accion")` como FastAPI dependency factory. Fail-closed: sin permiso explícito → 403.
- JWT access token poblado con los nombres de roles vigentes del usuario (informativo, no normativo).
- Migración 003 con seed de la matriz canónica (03_actores_y_roles.md §3.3).

**Non-Goals:**
- Filtrado `(propio)` a nivel de fila — eso es responsabilidad de cada módulo de dominio (C-07+).
- UI de gestión del catálogo RBAC — es para un change posterior.
- Caching de permisos — sin evidencia de problema de performance todavía.
- Impersonación — depende del audit log (C-05).

## Decisions

### 1. Permisos resueltos desde DB, no desde JWT

**Decisión**: el guard siempre consulta la DB para resolver permisos efectivos. El JWT solo lleva los nombres de roles (claim `roles`) con fines informativos (UI, logs), no como fuente de autorización.

**Alternativa descartada**: almacenar permisos en el JWT.
**Razón**: un permiso revocado quedaría activo hasta que expire el access token (15 min). Dado que estamos en un sistema de auditoría académica, la revocación debe ser inmediata.

### 2. `require_permission` como dependency factory (no middleware)

**Decisión**: `require_permission("modulo:accion")` devuelve una función de FastAPI dependency que se declara por endpoint. Cada endpoint declara explícitamente qué permiso necesita.

```python
@router.get("/calificaciones")
def get_calificaciones(
    current_user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
):
```

**Alternativa descartada**: middleware global con lista de rutas → permisos.
**Razón**: la dependency es explícita y colocated con el endpoint. El middleware implica una tabla de rutas que diverge del código con el tiempo.

### 3. Vigencia en `user_rol` con `desde` / `hasta`

**Decisión**: `user_rol` tiene `desde DATE NOT NULL` y `hasta DATE NULLABLE`. Una asignación es vigente si `desde <= today` y (`hasta IS NULL` OR `hasta >= today`). Los permisos efectivos se calculan solo sobre asignaciones vigentes.

**Razón**: la KB exige vigencia temporal (§5). Una asignación vencida no otorga permisos, pero se conserva (soft-delete prohibido aquí — auditoría).

### 4. Seed en migración Alembic (no script separado)

**Decisión**: la migración 003 aplica DDL y luego hace `INSERT` del seed con los roles base y la matriz canónica de permisos.

**Razón**: el seed es parte del estado mínimo del sistema. Un script separado puede ejecutarse en el orden incorrecto o no ejecutarse en un entorno nuevo.

### 5. NEXO sin permisos en el seed

**Decisión**: se crea el rol NEXO en el catálogo (cumpliendo la KB que lo lista como rol del dominio), pero sin permisos asignados en el seed inicial. Los permisos de NEXO se definen cuando PA-25 quede cerrada.

**Razón**: la pregunta abierta PA-25 describe que la semántica de NEXO no está definida aún.

### 6. Permiso `(propio)` modelado con sufijo `_propio` en el nombre

**Decisión implementada** (revisión de la decisión original): el catálogo usa permisos separados con sufijo `_propio` (e.g., `calificaciones:importar_propio` para PROFESOR, `calificaciones:importar` para COORDINADOR/ADMIN). La restricción `(propio)` sí se expresa en el nombre del permiso.

**Razón del cambio**: modelarlo en el catálogo permite al guard RBAC distinguir scope a nivel de declaración de endpoint, sin depender de la lógica del módulo de dominio. Los módulos (C-10+) pueden declarar `require_permission("calificaciones:importar")` para acceso global y `require_permission("calificaciones:importar_propio")` para acceso scoped — la semántica de "propio" sigue siendo responsabilidad del módulo, pero el catálogo refleja la distinción.

**Alternativa descartada originalmente**: un solo permiso `calificaciones:importar` con filtrado `(propio)` en dominio. Se descartó porque obligaría al módulo a re-chequear el scope DESPUÉS de que el guard ya autorizó — redundante e inconsistente con el modelo de permisos finos.

**Convención**: cualquier permiso con sufijo `_propio` indica scope reducido (solo datos propios del usuario). Los módulos de dominio son responsables de aplicar ese filtro en la query.

## Risks / Trade-offs

- **[Risk] DB hit por request en endpoints protegidos** → el query de permisos es simple (JOIN de 3 tablas, acotado por `user_id` + `tenant_id` + vigencia). Indexado correctamente es sub-milisegundo. Si en C-05+ se detecta latencia, se puede agregar cache en memoria con TTL.
- **[Risk] Seed en migración dificulta actualizaciones de la matriz** → la migración es inmutable por convención. Cambios al seed van en migraciones posteriores (INSERT/UPDATE). Documentado como convención.
- **[Risk] NEXO sin permisos puede confundir** → el rol existe en el catálogo pero no otorga acceso a nada. Un usuario con solo rol NEXO ve 403 en todo endpoint protegido. Documentado en seed como `# permisos pendientes PA-25`.

## Migration Plan

1. Aplicar migración 003 en un entorno con DB vacía o existente (idempotente por uso de `INSERT IF NOT EXISTS`).
2. Rollback: `alembic downgrade -1` → elimina tablas y seed.
3. No hay datos de usuarios existentes en producción todavía (aún en construcción).

## Open Questions

- **PA-25**: ¿Qué permisos tiene NEXO? Bloqueante para completar el seed de NEXO. Diferido.
