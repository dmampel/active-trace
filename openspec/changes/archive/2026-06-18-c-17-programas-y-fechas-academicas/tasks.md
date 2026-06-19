## 1. Migración y modelos

- [x] 1.1 Crear enum `TipoFechaAcademica` en `backend/app/models/fecha_academica.py` con valores `Parcial | TP | Coloquio | Recuperatorio`
- [x] 1.2 Crear modelo SQLAlchemy `ProgramaMateria` con campos: `id`, `tenant_id`, `materia_id`, `carrera_id`, `cohorte_id`, `titulo`, `referencia_archivo`, `cargado_at`, `deleted_at`; UniqueConstraint `(tenant_id, materia_id, carrera_id, cohorte_id)`
- [x] 1.3 Crear modelo SQLAlchemy `FechaAcademica` con campos: `id`, `tenant_id`, `materia_id`, `cohorte_id`, `tipo`, `numero`, `periodo`, `fecha`, `titulo`, `deleted_at`; UniqueConstraint `(tenant_id, materia_id, cohorte_id, tipo, numero, periodo)`
- [x] 1.4 Generar migración Alembic `017_programas_fechas_academicas`: tablas `programa_materia` y `fecha_academica` con índices en `(tenant_id, materia_id, carrera_id, cohorte_id)` y `(tenant_id, materia_id, cohorte_id, periodo)`
- [x] 1.5 Insertar permisos `estructura:gestionar` y `estructura:leer` en la migración de forma idempotente (INSERT ... ON CONFLICT DO NOTHING) si no existen ya
- [x] 1.6 Verificar que `alembic upgrade head` aplica sin errores en la DB de test

## 2. Schemas Pydantic

- [x] 2.1 Crear `ProgramaMateriaCreate` con `materia_id`, `carrera_id`, `cohorte_id`, `titulo`, `referencia_archivo` — `model_config = ConfigDict(extra='forbid')`
- [x] 2.2 Crear `ProgramaMateriaUpdate` con `titulo` (opt) y `referencia_archivo` (opt) — `extra='forbid'`
- [x] 2.3 Crear `ProgramaMateriaOut` con todos los campos públicos de `ProgramaMateria` incluyendo `cargado_at`
- [x] 2.4 Crear `FechaAcademicaCreate` con `materia_id`, `cohorte_id`, `tipo: TipoFechaAcademica`, `numero`, `periodo`, `fecha`, `titulo` — `extra='forbid'`
- [x] 2.5 Crear `FechaAcademicaUpdate` con todos los campos de negocio opcionales — `extra='forbid'`
- [x] 2.6 Crear `FechaAcademicaOut` con todos los campos públicos de `FechaAcademica`
- [x] 2.7 Crear `LMSFragmentOut` con campo `fragmento: str`

## 3. Repositorio — ProgramaMateria

- [x] 3.1 Crear `ProgramaMateriaRepository` en `backend/app/repositories/programa_materia_repository.py`
- [x] 3.2 Implementar `create(tenant_id, data) → ProgramaMateria`; captura `IntegrityError` y lanza excepción de conflicto
- [x] 3.3 Implementar `get_by_id(tenant_id, programa_id) → ProgramaMateria | None`
- [x] 3.4 Implementar `get_by_context(tenant_id, materia_id, carrera_id, cohorte_id) → ProgramaMateria | None`
- [x] 3.5 Implementar `update(tenant_id, programa_id, data) → ProgramaMateria`
- [x] 3.6 Implementar `soft_delete(tenant_id, programa_id) → None`; setea `deleted_at`

## 4. Repositorio — FechaAcademica

- [x] 4.1 Crear `FechaAcademicaRepository` en `backend/app/repositories/fecha_academica_repository.py`
- [x] 4.2 Implementar `create(tenant_id, data) → FechaAcademica`; captura `IntegrityError` y lanza excepción de conflicto
- [x] 4.3 Implementar `get_by_id(tenant_id, fecha_id) → FechaAcademica | None`
- [x] 4.4 Implementar `list(tenant_id, materia_id=None, cohorte_id=None, periodo=None) → list[FechaAcademica]` ordenado por `fecha` ascendente
- [x] 4.5 Implementar `update(tenant_id, fecha_id, data) → FechaAcademica`; captura `IntegrityError` para conflicto de unicidad
- [x] 4.6 Implementar `soft_delete(tenant_id, fecha_id) → None`

## 5. Servicios

- [x] 5.1 Crear `ProgramaMateriaService` en `backend/app/services/programa_materia_service.py`
- [x] 5.2 Implementar `crear(tenant_id, data)` → delega al repo; convierte `IntegrityError` a `HTTPException(409)`
- [x] 5.3 Implementar `get_by_id(tenant_id, id)` → lanza `404` si no encontrado
- [x] 5.4 Implementar `get_by_context(tenant_id, materia_id, carrera_id, cohorte_id)`
- [x] 5.5 Implementar `actualizar(tenant_id, id, data)` → lanza `404` si no encontrado
- [x] 5.6 Implementar `eliminar(tenant_id, id)` → lanza `404` si no encontrado
- [x] 5.7 Crear `FechaAcademicaService` en `backend/app/services/fecha_academica_service.py`
- [x] 5.8 Implementar `crear(tenant_id, data)` → delega al repo; convierte `IntegrityError` a `HTTPException(409)`
- [x] 5.9 Implementar `listar(tenant_id, materia_id, cohorte_id, periodo)`
- [x] 5.10 Implementar `actualizar(tenant_id, id, data)` → lanza `404` o `409` según corresponda
- [x] 5.11 Implementar `eliminar(tenant_id, id)` → lanza `404` si no encontrado
- [x] 5.12 Implementar `generar_fragmento_lms(tenant_id, materia_id, cohorte_id, periodo) → str` — construye texto Markdown con las fechas ordenadas cronológicamente

## 6. Routers

- [x] 6.1 Crear `backend/app/routers/programas.py` con prefix `/api/v1/programas`
- [x] 6.2 `POST /api/v1/programas` — `require_permission("estructura:gestionar")`, retorna 201
- [x] 6.3 `GET /api/v1/programas/{id}` — `require_permission("estructura:leer")`, retorna 200 o 404
- [x] 6.4 `GET /api/v1/programas` — `require_permission("estructura:leer")`, query params `materia_id`, `carrera_id`, `cohorte_id`
- [x] 6.5 `PATCH /api/v1/programas/{id}` — `require_permission("estructura:gestionar")`, retorna 200
- [x] 6.6 `DELETE /api/v1/programas/{id}` — `require_permission("estructura:gestionar")`, retorna 204
- [x] 6.7 Crear `backend/app/routers/fechas_academicas.py` con prefix `/api/v1/fechas-academicas`
- [x] 6.8 `POST /api/v1/fechas-academicas` — `require_permission("estructura:gestionar")`, retorna 201
- [x] 6.9 `GET /api/v1/fechas-academicas` — `require_permission("estructura:leer")`, query params `materia_id`, `cohorte_id`, `periodo`
- [x] 6.10 `GET /api/v1/fechas-academicas/{id}` — `require_permission("estructura:leer")`, retorna 200 o 404
- [x] 6.11 `PATCH /api/v1/fechas-academicas/{id}` — `require_permission("estructura:gestionar")`, retorna 200
- [x] 6.12 `DELETE /api/v1/fechas-academicas/{id}` — `require_permission("estructura:gestionar")`, retorna 204
- [x] 6.13 `GET /api/v1/fechas-academicas/lms-fragment` — `require_permission("estructura:leer")`, query params `materia_id`, `cohorte_id`, `periodo`, retorna `LMSFragmentOut`
- [x] 6.14 Registrar ambos routers en `backend/app/main.py`

## 7. Tests — Repositorio ProgramaMateria (DB real)

- [x] 7.1 Safety net: ejecutar suite existente y capturar baseline de tests pasando
- [x] 7.2 Test RED→GREEN: `create` persiste `ProgramaMateria` con tenant correcto
- [x] 7.3 Test RED→GREEN: `create` para contexto duplicado lanza excepción de conflicto (unicidad)
- [x] 7.4 Test RED→GREEN: `get_by_id` con programa de otro tenant retorna `None` (aislamiento)
- [x] 7.5 Test RED→GREEN: `get_by_context` retorna el programa correcto
- [x] 7.6 Test RED→GREEN: `update` modifica solo los campos enviados
- [x] 7.7 Test RED→GREEN: `soft_delete` → consulta posterior retorna `None`

## 8. Tests — Repositorio FechaAcademica (DB real)

- [x] 8.1 Test RED→GREEN: `create` persiste `FechaAcademica` con tenant correcto
- [x] 8.2 Test RED→GREEN: `create` duplicado (mismo tipo/numero/periodo) lanza excepción de conflicto
- [x] 8.3 Test RED→GREEN: `get_by_id` con fecha de otro tenant retorna `None` (aislamiento)
- [x] 8.4 Test RED→GREEN: `list` filtra por `materia_id`, `cohorte_id` y `periodo` correctamente
- [x] 8.5 Test RED→GREEN: `list` devuelve resultados ordenados por `fecha` ascendente
- [x] 8.6 Test RED→GREEN: `update` genera 409 si viola unicidad con otro registro
- [x] 8.7 Test RED→GREEN: `soft_delete` → consulta posterior retorna `None`

## 9. Tests — Routers (TestClient + mocked services)

- [x] 9.1 Test: `POST /api/v1/programas` sin token retorna 401
- [x] 9.2 Test: `POST /api/v1/programas` sin permiso `estructura:gestionar` retorna 403
- [x] 9.3 Test: `POST /api/v1/programas` válido retorna 201 con datos
- [x] 9.4 Test: `POST /api/v1/programas` con contexto duplicado retorna 409
- [x] 9.5 Test: `GET /api/v1/programas/{id}` inexistente retorna 404
- [x] 9.6 Test: `DELETE /api/v1/programas/{id}` válido retorna 204
- [x] 9.7 Test: `POST /api/v1/fechas-academicas` con tipo inválido retorna 422
- [x] 9.8 Test: `POST /api/v1/fechas-academicas` válido retorna 201
- [x] 9.9 Test: `GET /api/v1/fechas-academicas` filtra correctamente por query params
- [x] 9.10 Test: `GET /api/v1/fechas-academicas/lms-fragment` con datos retorna fragmento Markdown no vacío
- [x] 9.11 Test: `GET /api/v1/fechas-academicas/lms-fragment` sin fechas retorna fragmento vacío o mensaje de ausencia
