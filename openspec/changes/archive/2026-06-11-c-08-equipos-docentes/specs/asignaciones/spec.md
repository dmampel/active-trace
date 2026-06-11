## MODIFIED Requirements

### Requirement: CRUD de asignaciones permisado y auditado

El sistema SHALL permitir a usuarios con permiso `equipos:asignar` (COORDINADOR, ADMIN) crear, leer, editar y eliminar (soft delete) asignaciones a través de `/api/v1/asignaciones`. Toda mutación MUST registrar un evento de auditoría `ASIGNACION_MODIFICAR`. La identidad y el tenant se derivan del JWT; los IDs de contexto del body se validan contra el tenant de la sesión. El endpoint `GET /api/v1/asignaciones` MUST aceptar los filtros adicionales `carrera_id`, `cohorte_id`, `materia_id` y `rol` para la vista de coordinador/admin (F4.3).

#### Scenario: Crear asignación exitosamente
- **WHEN** un usuario con permiso `equipos:asignar` envía POST `/api/v1/asignaciones` con `usuario_id`, `rol`, `desde` y contexto válidos del tenant
- **THEN** el sistema crea la asignación y retorna 201, y registra `ASIGNACION_MODIFICAR` en auditoría

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `equipos:asignar` intenta POST `/api/v1/asignaciones`
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Contexto de otro tenant rechazado
- **WHEN** un usuario con permiso `equipos:asignar` del tenant A intenta crear una asignación referenciando una `materia_id` que pertenece al tenant B
- **THEN** el sistema retorna 422 Unprocessable Entity y no crea la asignación

#### Scenario: Filtrar asignaciones por usuario
- **WHEN** un usuario con permiso `equipos:asignar` solicita GET `/api/v1/asignaciones?usuario_id={id}`
- **THEN** el sistema retorna las asignaciones (no eliminadas) de ese usuario dentro del tenant del autenticado

#### Scenario: Filtrar asignaciones por carrera y cohorte
- **WHEN** un usuario con permiso `equipos:asignar` solicita GET `/api/v1/asignaciones?carrera_id={id}&cohorte_id={id}`
- **THEN** el sistema retorna las asignaciones (no eliminadas) que coinciden con ambos filtros dentro del tenant

#### Scenario: Filtrar asignaciones por rol
- **WHEN** un usuario con permiso `equipos:asignar` solicita GET `/api/v1/asignaciones?rol=PROFESOR`
- **THEN** el sistema retorna las asignaciones (no eliminadas) con `rol = PROFESOR` dentro del tenant

#### Scenario: Editar vigencia de asignación
- **WHEN** un usuario con permiso `equipos:asignar` envía PATCH `/api/v1/asignaciones/{id}` modificando `hasta`
- **THEN** el sistema actualiza la fecha, retorna 200 y registra `ASIGNACION_MODIFICAR`
