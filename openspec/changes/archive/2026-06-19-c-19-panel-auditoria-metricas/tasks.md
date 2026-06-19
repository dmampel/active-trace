# Tasks — C-19 panel-auditoria-metricas

> Strict TDD en cada grupo: test que falla → código mínimo → triangulación → refactor.
> Tests sin mocks de DB (base real efímera). Cobertura ≥80% líneas, ≥90% reglas de negocio.
> Governance ALTO: la implementación requiere aprobación humana explícita antes de escribir código.

## 1. Permiso RBAC y configuración

- [x] 1.1 Agregar a `app/core/config.py` los parámetros del log de últimas acciones: `auditoria_log_limite_default` (200) y `auditoria_log_limite_max` (p. ej. 1000), con valores por defecto.
- [x] 1.2 Crear migración Alembic `019_auditoria_permiso` (down_revision `b2c3d4e5f6a7`) que siembra el permiso `auditoria:ver` y los `rol_permiso` para ADMIN, COORDINADOR y FINANZAS. `downgrade` borra el permiso por nombre. Calcar `010_analisis_permiso`. Sin DDL de tablas.

## 2. Schemas (Pydantic v2)

- [x] 2.1 Crear `app/schemas/auditoria.py` con DTOs response, todos con `model_config = ConfigDict(extra='forbid')`: `AuditLogEntryResponse` (fecha_hora, actor_id, impersonado_id, materia_id, accion, filas_afectadas, ip, user_agent), `LogCompletoResponse` (paginado: total, page, page_size, items), `AccionPorDiaItem`/`AccionesPorDiaResponse`, `EstadoComunicacionesDocenteItem`/`EstadoComunicacionesResponse`, `InteraccionDocenteMateriaItem`/`InteraccionesResponse`, `UltimasAccionesResponse`.

## 3. Repository de lectura/agregación (sin mocks de DB)

- [x] 3.1 RED+GREEN: `AuditoriaRepository.list_log(...)` — filtros opcionales fecha_desde/fecha_hasta, materia_id, usuario_id, accion; `WHERE tenant_id` siempre; orden por `fecha_hora` desc; paginado. Triangular con ≥2 casos (con/sin filtros) + escenario de aislamiento de tenant.
- [x] 3.2 RED+GREEN: `AuditoriaRepository.acciones_por_dia(...)` con `func.date(fecha_hora)` + `group_by`, scope tenant/materia. Triangular: distribución multi-día y día sin actividad.
- [x] 3.3 RED+GREEN: `AuditoriaRepository.estado_comunicaciones_por_docente(...)` sobre `comunicacion` agrupando por `enviado_por` + `estado` (+ materia), scope tenant/materia. Triangular: docente con varios estados.
- [x] 3.4 RED+GREEN: `AuditoriaRepository.interacciones_por_docente_materia(...)` agrupando por actor_id, materia_id, accion. Triangular: conteo por (docente, materia, acción).
- [x] 3.5 RED+GREEN: `AuditoriaRepository.ultimas_acciones(limite, materia_ids, ...)` orden desc, `LIMIT`. Triangular: límite por defecto vs límite custom.
- [x] 3.6 Verificar que el repo NO expone create/update/delete sobre AuditLog (solo lectura).

## 4. Service (reglas de negocio: scope + límite)

- [x] 4.1 RED+GREEN: `AuditoriaService` resuelve scope — ADMIN/FINANZAS sin restricción de materia; COORDINADOR (no ADMIN) → `materia_ids` desde asignaciones COORDINADOR vigentes (`AsignacionRepository`). Triangular: ADMIN ve todo vs COORDINADOR ve solo sus materias.
- [x] 4.2 RED+GREEN: scope borde — coordinador sin materias coordinadas → vacío en endpoints por materia; filtro a materia ajena → intersección vacía; registros con `materia_id NULL` excluidos para COORDINADOR e incluidos para ADMIN.
- [x] 4.3 RED+GREEN: clamp del límite de últimas acciones — `limite <= 0 → default`; `limite > max → max`; `limite` válido respetado. Triangular los 3 casos.
- [x] 4.4 RED+GREEN: métodos del service que envuelven cada agregación del repo, aplicando scope y devolviendo los DTOs. Identidad/tenant siempre desde `CurrentUser`.

## 5. Router `/api/v1/auditoria/*`

- [x] 5.1 Crear `app/api/v1/routers/auditoria.py` con dependency factory `_get_auditoria_service` y los endpoints: `GET /log`, `GET /acciones-por-dia`, `GET /comunicaciones-por-docente`, `GET /interacciones`, `GET /ultimas-acciones`. Todos con `dependencies=[Depends(require_permission("auditoria:ver"))]` y `current_user=Depends(get_current_user)`.
- [x] 5.2 RED+GREEN (integración): usuario sin `auditoria:ver` → 403 en cada endpoint; usuario con permiso → 200. Triangular roles (PROFESOR=403, ADMIN/COORDINADOR/FINANZAS=200).
- [x] 5.3 RED+GREEN (integración): aislamiento de tenant end-to-end — ADMIN del tenant A no ve registros del tenant B.
- [x] 5.4 RED+GREEN (integración): `tenant_id`/`usuario_id` en query distintos al JWT son ignorados (scope sale del JWT).
- [x] 5.5 RED+GREEN (integración): consultar el panel NO crea registros nuevos en `AuditLog` (conteo invariante antes/después).
- [x] 5.6 Registrar el router en la app (`app/api/v1/routers/__init__.py` o donde se monten los routers v1).

## 6. Cierre

- [x] 6.1 Correr la suite completa de C-19 + verificar que no se rompió ninguna suite previa (audit_log, analisis, comunicacion). Confirmar cobertura ≥80% líneas / ≥90% reglas de negocio.
- [x] 6.2 Verificar reglas duras: snake_case, `extra='forbid'`, ≤500 LOC/archivo, sin lógica en router, sin acceso directo a DB desde service, una sola migración.
- [x] 6.3 Marcar C-19 como `[x]` en `CHANGES.md` al archivar.



