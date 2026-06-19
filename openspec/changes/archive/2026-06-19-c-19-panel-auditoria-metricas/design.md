## Context

C-05 ya persiste `AuditLog` (modelo en `app/models/audit_log.py`) de forma append-only: cada acción significativa escribe `fecha_hora`, `actor_id`, `impersonado_id`, `materia_id`, `accion` (código del catálogo cerrado RN-24), `detalle` (JSONB), `filas_afectadas`, `ip`, `user_agent`, todo con `tenant_id` (TenantMixin). El `AuditLogRepository` actual es exclusivamente de escritura (`create_entry`) y bloquea `update`/`delete`. No existe ninguna ruta de lectura.

C-04 provee el guard `require_permission("modulo:accion")` (fail-closed → 403) y `RbacRepository.get_effective_permissions`. C-07 provee `AsignacionRepository` con `list_vigentes(tenant_id, user_id)` y `derive_estado_vigencia`, que permiten resolver las materias coordinadas por un usuario. C-12 escribe `Comunicacion` con `enviado_por`, `materia_id` y `estado` (enum `EstadoComunicacion`: Pendiente/Enviando/Enviado/Error/Cancelado).

C-19 agrega la capa de **lectura** sobre ese log: dashboards (F9.1) y log completo con filtros (F9.2), con scope `(propio)` para COORDINADOR. Patrón de referencia directo: el router/service de análisis (C-11), que ya implementa scope por rol y guard RBAC.

## Goals / Non-Goals

**Goals:**
- Endpoints de solo lectura bajo `/api/v1/auditoria/*` con guard `auditoria:ver`, fail-closed.
- Agregaciones: acciones por día, estado de comunicaciones por docente, interacciones por docente×materia, log de últimas acciones (límite configurable, defecto 200, con tope máximo).
- Log completo paginado con filtros combinables: rango de fechas, materia, usuario, código de acción.
- Scope `(propio)` del COORDINADOR resuelto vía asignaciones COORDINADOR vigentes; ADMIN/FINANZAS ven todo el tenant.
- Aislamiento estricto por `tenant_id` en cada query.
- Sembrar el permiso `auditoria:ver` a ADMIN, COORDINADOR, FINANZAS por migración Alembic.

**Non-Goals:**
- No se escribe, modifica ni borra `AuditLog` (sigue append-only). Las consultas del panel NO se auto-auditan.
- No se crea ni altera ninguna tabla (solo se siembra un permiso).
- Sin frontend (lo consume C-24).
- Sin export CSV de auditoría en este change (no está en el scope de C-19; se puede proponer aparte).
- Sin descifrado de PII: el panel agrega y lista metadatos de auditoría, no datos personales cifrados.

## Decisions

### 1. Repositorio de lectura separado del de escritura
Crear `AuditoriaRepository` (lectura/agregación) en vez de ensanchar `AuditLogRepository` (que es deliberadamente append-only de escritura y bloquea `update`/`delete`). Mantiene la responsabilidad única y deja intacto el contrato de inmutabilidad de C-05. Las agregaciones (por día, por docente×materia, por estado) se hacen con `func.count`, `func.date(fecha_hora)` y `group_by` en SQLAlchemy, siempre con `tenant_id` en el `WHERE`.

### 2. Resolución de scope en el Service, no en el Router ni el Repo
`AuditoriaService` decide el scope: si el usuario es ADMIN o FINANZAS → sin restricción de materia; si es COORDINADOR (y no ADMIN) → resuelve `materia_ids` coordinadas vía `AsignacionRepository` (asignaciones rol COORDINADOR vigentes) y las pasa como restricción `WHERE materia_id IN (...)` al repositorio. Espejo del patrón `_tiene_scope_global` / `_resolver_asignacion_id` de `AnalisisService`. El repositorio recibe el filtro de materias ya resuelto y nunca decide permisos.

Caso borde: un filtro explícito de `materia_id` que cae fuera del scope del coordinador se intersecta con su scope → resultado vacío (el filtro nunca amplía el scope). Un coordinador sin materias coordinadas → lista de materias vacía → endpoints scopeados por materia devuelven vacío.

### 3. Límite del log de últimas acciones: config + clamp en el service
El defecto (200) y el tope máximo viven en `app/core/config.py` (Settings). El service aplica el clamp: `limite <= 0 → defecto`; `limite > maximo → maximo`. Evita que un cliente pida millones de filas. El router expone `limite` como query opcional; la lógica de saneamiento es del service (regla de negocio testeable), no del router.

### 4. Estado de comunicaciones leído desde `Comunicacion`, no desde `AuditLog`
El "estado por docente" (F9.1) es la distribución real de `EstadoComunicacion` agrupada por `enviado_por` y `materia_id` sobre la tabla `comunicacion` — no un derivado del log. Es la fuente de verdad del estado del worker. El `AuditoriaRepository` consulta `comunicacion` con el mismo scope de materia/tenant. Reusa los estados existentes (Pendiente/Enviando/Enviado/Error/Cancelado) sin redefinirlos.

### 5. Schemas Pydantic v2 con extra='forbid'
DTOs en `app/schemas/auditoria.py`: `AuditLogEntryResponse`, `AccionesPorDiaResponse`, `EstadoComunicacionesPorDocenteResponse`, `InteraccionesPorDocenteMateriaResponse`, `LogCompletoResponse` (paginado), todos con `model_config = ConfigDict(extra='forbid')`. Filtros como query params tipados en el router (uuid/date/str opcionales).

### 6. Migración de permiso, sin DDL
Migración `019_auditoria_permiso` (down_revision `b2c3d4e5f6a7`, head actual = 018_liquidaciones). Inserta `permiso` `auditoria:ver` y los `rol_permiso` para ADMIN, COORDINADOR, FINANZAS. Calca `010_analisis_permiso`. `downgrade` borra el permiso por nombre. Una sola migración por cambio de schema (regla dura).

### 7. Endpoints
- `GET /api/v1/auditoria/log` — log completo paginado + filtros (fecha_desde, fecha_hasta, materia_id, usuario_id, accion, page, page_size).
- `GET /api/v1/auditoria/acciones-por-dia` — serie temporal (+ rango fechas opcional).
- `GET /api/v1/auditoria/comunicaciones-por-docente` — distribución de estados.
- `GET /api/v1/auditoria/interacciones` — conteo docente×materia×acción.
- `GET /api/v1/auditoria/ultimas-acciones?limite=` — últimas N (defecto 200, clamp al máximo).

Todos: `dependencies=[Depends(require_permission("auditoria:ver"))]`, `current_user` vía `get_current_user`, service vía dependency factory (patrón `_get_analisis_service`).

## Risks / Trade-offs

- **Performance de agregaciones sobre `audit_log`**: la tabla crece sin límite (append-only). Las agregaciones por día/docente/materia pueden volverse caras. Mitigación: filtrar siempre por `tenant_id` (ya indexado por TenantMixin) y acotar por rango de fechas; las queries usan `group_by` en DB (no en Python). Si escala mal, un índice compuesto `(tenant_id, fecha_hora)` o `(tenant_id, actor_id, materia_id)` es el siguiente paso — se deja anotado pero fuera de scope salvo que los tests de volumen lo exijan.
- **Scope `(propio)` y materias sin `materia_id` en el log**: algunas acciones se registran con `materia_id = NULL` (p. ej. acciones globales como impersonación). Decisión: para COORDINADOR, los registros con `materia_id NULL` NO entran en su scope (no son de "sus materias"); ADMIN sí los ve. Esto se cubre con un escenario de test explícito.
- **Doble fuente de "estado de comunicaciones"** (tabla `comunicacion` vs log): elegimos la tabla por ser la verdad del estado actual; el log solo registra el evento de envío, no las transiciones posteriores del worker. Trade-off aceptado y documentado.
- **Gobernanza ALTO**: el dominio es auditoría. El riesgo se minimiza porque la superficie es 100% lectura sobre un log inmutable; no hay forma de que C-19 corrompa el log. Aún así, la implementación (apply) requiere aprobación humana explícita antes de escribir código.
