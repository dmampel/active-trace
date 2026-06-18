## 1. Migración y modelos

- [x] 1.1 Crear `backend/app/models/evaluacion.py` con `Evaluacion` (id, tenant_id, materia_id, cohorte_id, tipo enum, instancia, cupos_por_dia JSONB, deleted_at)
- [x] 1.2 Agregar modelo `EvaluacionAlumno` (evaluacion_id, alumno_id, tenant_id) — tabla asociativa de convocados
- [x] 1.3 Crear modelo `ReservaEvaluacion` (id, tenant_id, evaluacion_id, alumno_id, fecha_hora, estado enum Activa/Cancelada)
- [x] 1.4 Crear modelo `ResultadoEvaluacion` (id, tenant_id, evaluacion_id, alumno_id, nota_final texto)
- [x] 1.5 Crear modelo `FechaAcademica` (id, tenant_id, materia_id, cohorte_id, tipo enum, numero, periodo, fecha, titulo)
- [x] 1.6 Registrar todos los modelos en `backend/app/models/__init__.py` y en `Base.metadata`
- [x] 1.7 Generar migración Alembic: `alembic revision --autogenerate -m "evaluaciones_coloquios_fechas_academicas"`
- [x] 1.8 Verificar migración generada (columnas, FKs, índices tenant_id, deleted_at en Evaluacion) y aplicar en DB test

## 2. Schemas Pydantic

- [x] 2.1 Crear `backend/app/schemas/evaluacion.py`: `EvaluacionCreate`, `EvaluacionRead`, `EvaluacionUpdate` (extra='forbid' en todos)
- [x] 2.2 Agregar `EvaluacionAlumnoImportRequest` (lista de alumno_ids) y `EvaluacionAlumnoImportResult`
- [x] 2.3 Agregar `ReservaEvaluacionCreate` (evaluacion_id, fecha), `ReservaEvaluacionRead`
- [x] 2.4 Agregar `ResultadoEvaluacionUpsert` (alumno_id, nota_final), `ResultadoEvaluacionRead`
- [x] 2.5 Agregar `MetricasColoquioRead` (total_convocados, instancias_activas, reservas_activas, notas_registradas)
- [x] 2.6 Crear `backend/app/schemas/fecha_academica.py`: `FechaAcademicaCreate`, `FechaAcademicaRead`, `FechaAcademicaUpdate`

## 3. Permisos RBAC

- [x] 3.1 Agregar permisos `coloquios:gestionar`, `coloquios:ver`, `coloquios:reservar`, `fechas_academicas:gestionar`, `fechas_academicas:ver` en el seed/fixture de RBAC (mismo patrón de C-04)
- [x] 3.2 Asignar permisos a roles: COORDINADOR y ADMIN → `coloquios:gestionar`, `coloquios:ver`; ALUMNO → `coloquios:reservar`; COORDINADOR, ADMIN, PROFESOR → `fechas_academicas:gestionar`; todos los roles → `fechas_academicas:ver`

## 4. Repositories

- [x] 4.1 Crear `backend/app/repositories/evaluacion_repository.py` con `EvaluacionRepository`: `create`, `get_by_id`, `list_by_tenant` (excluye soft deleted), `soft_delete`
- [x] 4.2 Agregar `import_alumnos` (upsert masivo en `evaluacion_alumno` con validación de tenant)
- [x] 4.3 Agregar `get_metricas` (query agregado: convocados, instancias activas, reservas activas, notas)
- [x] 4.4 Agregar `get_agenda` (ReservaEvaluacion activas por evaluacion_id con datos de alumno)
- [x] 4.5 Agregar `get_resultados` (ResultadoEvaluacion por evaluacion_id, incluyendo soft deleted de Evaluacion para admin)
- [x] 4.6 Implementar `reservar_turno` con UPDATE atómico: `UPDATE evaluacion SET cupos_por_dia = jsonb_set(...) WHERE id=:id AND (cupos_por_dia->:fecha)::int > 0 RETURNING id`; si no retorna fila → raise ConflictError
- [x] 4.7 Implementar `cancelar_reserva`: marca estado=Cancelada y restaura cupo en JSONB
- [x] 4.8 Implementar `upsert_resultado` (ON CONFLICT DO UPDATE por evaluacion_id + alumno_id)
- [x] 4.9 Crear `backend/app/repositories/fecha_academica_repository.py`: `create`, `list_by_tenant` con filtros opcionales (materia_id, cohorte_id, tipo), `update`, `soft_delete`

## 5. Services

- [x] 5.1 Crear `backend/app/services/evaluacion_service.py` con `EvaluacionService`: orquesta CRUD y delega a `EvaluacionRepository`
- [x] 5.2 Implementar `importar_alumnos`: valida que alumno_ids sean del tenant (consulta UsuarioRepository), llama `import_alumnos` del repository
- [x] 5.3 Implementar `reservar_turno`: valida que ALUMNO esté en `evaluacion_alumno`, no tenga reserva activa, llama `reservar_turno` del repository; propaga ConflictError
- [x] 5.4 Implementar `cancelar_reserva`: valida que reserva pertenece al alumno autenticado, llama `cancelar_reserva` del repository
- [x] 5.5 Implementar `get_metricas`: delega a repository y retorna `MetricasColoquioRead`
- [x] 5.6 Implementar `upsert_resultado`: valida tenant, delega a repository
- [x] 5.7 Crear `backend/app/services/fecha_academica_service.py`: `create`, `list` con filtros, `update`, `delete`

## 6. Routers / API

- [x] 6.1 Crear `backend/app/api/v1/routers/coloquios.py` con los endpoints:
  - `POST /api/coloquios` — `require_permission("coloquios:gestionar")`
  - `GET /api/coloquios` — `require_permission("coloquios:ver")`
  - `GET /api/coloquios/metricas` — `require_permission("coloquios:ver")`
  - `GET /api/coloquios/{id}` — `require_permission("coloquios:ver")`
  - `PUT /api/coloquios/{id}` — `require_permission("coloquios:gestionar")`
  - `DELETE /api/coloquios/{id}` — `require_permission("coloquios:gestionar")`
  - `POST /api/coloquios/{id}/alumnos` — `require_permission("coloquios:gestionar")`
  - `POST /api/coloquios/{id}/reservar` — `require_permission("coloquios:reservar")`
  - `DELETE /api/coloquios/{id}/reservar` — `require_permission("coloquios:reservar")`
  - `GET /api/coloquios/{id}/agenda` — `require_permission("coloquios:ver")`
  - `POST /api/coloquios/{id}/resultados` — `require_permission("coloquios:gestionar")`
  - `GET /api/coloquios/{id}/resultados` — `require_permission("coloquios:ver")`
- [x] 6.2 Crear `backend/app/api/v1/routers/fechas_academicas.py`:
  - `POST /api/fechas-academicas` — `require_permission("fechas_academicas:gestionar")`
  - `GET /api/fechas-academicas` — `require_permission("fechas_academicas:ver")`
  - `PUT /api/fechas-academicas/{id}` — `require_permission("fechas_academicas:gestionar")`
  - `DELETE /api/fechas-academicas/{id}` — `require_permission("fechas_academicas:gestionar")`
- [x] 6.3 Registrar ambos routers en `backend/app/api/v1/router.py`
- [x] 6.4 Verificar que identidad y tenant_id SIEMPRE vienen de la sesión JWT (nunca del body)

## 7. Tests — Coloquios (TDD)

- [x] 7.1 Test: crear convocatoria — exitoso, campo faltante (422), ALUMNO sin permiso (403)
- [x] 7.2 Test: importar alumnos — exitoso, alumno de otro tenant rechazado
- [x] 7.3 Test: reservar turno — exitoso, cupo agotado (409), alumno no habilitado (403), reserva duplicada (409)
- [x] 7.4 Test: cancelar reserva — exitosa, sin reserva activa (404)
- [x] 7.5 Test: UPDATE atómico de cupo — dos reservas concurrentes en el mismo slot, solo una debe pasar (race condition test con dos sessions)
- [x] 7.6 Test: listar convocatorias — ve solo las del tenant, lista vacía
- [x] 7.7 Test: métricas — valores correctos con datos, todo cero sin datos
- [x] 7.8 Test: upsert resultado — crear, actualizar, nota texto y nota numérica
- [x] 7.9 Test: agenda — agrupada por fecha, vacía
- [x] 7.10 Test: soft delete — convocatoria eliminada no aparece en list; resultados siguen accesibles
- [x] 7.11 Test: multi-tenancy — consultas de tenant_A no ven datos de tenant_B

## 8. Tests — Fechas Académicas (TDD)

- [x] 8.1 Test: crear fecha académica — exitosa, tipo inválido (422), sin permiso (403)
- [x] 8.2 Test: listar fechas con filtros — por materia_id, por cohorte_id, combinado
- [x] 8.3 Test: editar y eliminar fecha académica
- [x] 8.4 Test: aislamiento de tenant en fechas académicas
