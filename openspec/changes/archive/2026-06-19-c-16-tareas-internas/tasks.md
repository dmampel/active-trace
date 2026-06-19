## 1. Migración y modelos

- [x] 1.1 Crear enum `EstadoTarea` en `backend/app/models/tarea.py` con valores `pendiente | en_progreso | resuelta | cancelada`
- [x] 1.2 Crear modelo SQLAlchemy `Tarea` con campos: `id`, `tenant_id`, `materia_id` (nullable), `asignado_a`, `asignado_por`, `estado`, `descripcion`, `contexto_id` (nullable), `deleted_at`
- [x] 1.3 Crear modelo SQLAlchemy `ComentarioTarea` con campos: `id`, `tenant_id`, `tarea_id`, `autor_id`, `texto`, `creado_at`
- [x] 1.4 Generar migración Alembic `016_tareas_internas`: tablas `tarea` y `comentario_tarea`, índices en `(tenant_id, asignado_a, estado)` y `(tenant_id, asignado_por, estado)`
- [x] 1.5 Insertar permiso `tareas:gestionar` en la migración de forma idempotente (INSERT ... ON CONFLICT DO NOTHING)
- [x] 1.6 Verificar que `alembic upgrade head` aplica sin errores en la DB de test

## 2. Schemas Pydantic

- [x] 2.1 Crear `TareaCreate` con `asignado_a`, `descripcion`, `materia_id` (opt), `contexto_id` (opt) — `model_config = ConfigDict(extra='forbid')`
- [x] 2.2 Crear `TareaOut` con todos los campos públicos de `Tarea` incluyendo `estado`
- [x] 2.3 Crear `TareaEstadoUpdate` con campo `estado: EstadoTarea` — `extra='forbid'`
- [x] 2.4 Crear `ComentarioCreate` con campo `texto` — `extra='forbid'`
- [x] 2.5 Crear `ComentarioOut` con `id`, `autor_id`, `texto`, `creado_at`
- [x] 2.6 Crear `PaginatedTareas` con `total`, `page`, `size`, `items: list[TareaOut]`

## 3. Repositorio

- [x] 3.1 Crear `TareaRepository` en `backend/app/repositories/tarea_repository.py`
- [x] 3.2 Implementar `create(tenant_id, asignado_por, data) → Tarea`
- [x] 3.3 Implementar `get_by_id(tenant_id, tarea_id) → Tarea | None` (filtra por tenant)
- [x] 3.4 Implementar `list_mis_tareas(tenant_id, asignado_a, estado=None) → list[Tarea]`
- [x] 3.5 Implementar `list_all(tenant_id, filters, page, size) → tuple[list[Tarea], int]` (admin global)
- [x] 3.6 Implementar `update_estado(tenant_id, tarea_id, nuevo_estado) → Tarea`
- [x] 3.7 Crear `ComentarioTareaRepository` con `create(tenant_id, tarea_id, autor_id, texto) → ComentarioTarea`
- [x] 3.8 Implementar `list_comentarios(tenant_id, tarea_id) → list[ComentarioTarea]` ordenados por `creado_at` asc

## 4. Servicio

- [x] 4.1 Crear `TareaService` en `backend/app/services/tarea_service.py`
- [x] 4.2 Implementar `crear_tarea(tenant_id, asignado_por, data)` — valida que `asignado_a` pertenezca al tenant
- [x] 4.3 Declarar `TRANSICIONES` dict y método `_validar_transicion(estado_actual, nuevo_estado)` que lanza `ValueError` si es inválida
- [x] 4.4 Implementar `cambiar_estado(tenant_id, tarea_id, nuevo_estado, usuario_id)` — valida transición y autorización (involucrados o COORDINADOR/ADMIN)
- [x] 4.5 Implementar `agregar_comentario(tenant_id, tarea_id, autor_id, texto)` — valida que la tarea exista en el tenant
- [x] 4.6 Implementar `mis_tareas(tenant_id, asignado_a, estado)` → delega al repo
- [x] 4.7 Implementar `listar_todas(tenant_id, rol, filters, page, size)` — lanza `PermissionError` si rol no es COORDINADOR/ADMIN

## 5. Router

- [x] 5.1 Crear `backend/app/routers/tareas.py` con prefix `/api/tareas`
- [x] 5.2 `POST /api/tareas` — `require_permission("tareas:gestionar")`, crea tarea, retorna 201
- [x] 5.3 `GET /api/tareas/mis-tareas` — `require_permission("tareas:gestionar")`, query param `estado` opcional
- [x] 5.4 `PATCH /api/tareas/{tarea_id}/estado` — `require_permission("tareas:gestionar")`, valida transición, retorna 200
- [x] 5.5 `POST /api/tareas/{tarea_id}/comentarios` — `require_permission("tareas:gestionar")`, retorna 201
- [x] 5.6 `GET /api/tareas/{tarea_id}/comentarios` — `require_permission("tareas:gestionar")`, retorna lista ordenada
- [x] 5.7 `GET /api/tareas` — `require_permission("tareas:gestionar")` + check rol COORDINADOR/ADMIN, filtros + paginación
- [x] 5.8 Registrar router en `backend/app/main.py`

## 6. Tests — Repositorio (DB real, sin mocks)

- [x] 6.1 Safety net: ejecutar suite existente y capturar baseline de tests pasando
- [x] 6.2 Test: `create` persiste tarea con `estado=pendiente` y `tenant_id` correcto
- [x] 6.3 Test: `get_by_id` con tarea de otro tenant retorna `None` (aislamiento)
- [x] 6.4 Test: `list_mis_tareas` filtra por `asignado_a` y `estado`
- [x] 6.5 Test: `list_all` retorna paginación correcta con filtros combinados
- [x] 6.6 Test: `update_estado` persiste nuevo estado
- [x] 6.7 Test: `create` de comentario y `list_comentarios` en orden cronológico

## 7. Tests — Servicio (unitarios con repo mockeado)

- [x] 7.1 Test: `crear_tarea` con `asignado_a` de otro tenant lanza error
- [x] 7.2 Test: `_validar_transicion` — todas las transiciones válidas pasan
- [x] 7.3 Test: `_validar_transicion` — estado terminal (`resuelta`) lanza `ValueError`
- [x] 7.4 Test: `cambiar_estado` por usuario no involucrado lanza `PermissionError`
- [x] 7.5 Test: `listar_todas` con rol no-admin lanza `PermissionError`

## 8. Tests — Router (TestClient + servicio mockeado)

- [x] 8.1 Test: `POST /api/tareas` sin permiso → 403
- [x] 8.2 Test: `POST /api/tareas` con datos válidos → 201 + TareaOut
- [x] 8.3 Test: `GET /api/tareas/mis-tareas` → 200 con lista filtrada
- [x] 8.4 Test: `PATCH /api/tareas/{id}/estado` transición válida → 200
- [x] 8.5 Test: `PATCH /api/tareas/{id}/estado` transición inválida → 422
- [x] 8.6 Test: `POST /api/tareas/{id}/comentarios` → 201 + ComentarioOut
- [x] 8.7 Test: `GET /api/tareas` sin rol admin → 403
- [x] 8.8 Test: `GET /api/tareas` con rol admin + filtros → 200 paginado
