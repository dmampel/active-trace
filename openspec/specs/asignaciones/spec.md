## ADDED Requirements

### Requirement: Modelo de Asignación contextual

El sistema SHALL modelar la `Asignacion` como el vínculo entre un usuario, un rol del dominio (PROFESOR, TUTOR, COORDINADOR, NEXO, ADMIN, FINANZAS) y un contexto académico (materia, carrera, cohorte, comisiones). Cada asignación tiene `desde` (obligatoria) y `hasta` (opcional, nulo = vigencia abierta), un `responsable_id` opcional (jerarquía: a quién rinde cuentas el asignado) y un `estado_vigencia` (Vigente/Vencida) que MUST derivarse de las fechas y NO almacenarse. Los campos de contexto (`materia_id`, `carrera_id`, `cohorte_id`) son nullables para roles de alcance de tenant global.

#### Scenario: Estado de vigencia derivado por fechas
- **WHEN** se consulta una asignación con `desde <= hoy` y (`hasta` nulo o `hoy <= hasta`)
- **THEN** su `estado_vigencia` derivado es `Vigente`

#### Scenario: Asignación con hasta en el pasado es Vencida
- **WHEN** se consulta una asignación cuyo `hasta` es anterior a la fecha actual
- **THEN** su `estado_vigencia` derivado es `Vencida`

#### Scenario: Asignación con contexto global
- **WHEN** se crea una asignación de un rol de tenant global sin `materia_id`, `carrera_id` ni `cohorte_id`
- **THEN** el sistema acepta la asignación con esos campos nulos

---

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

---

### Requirement: Histórico de asignaciones append-only

El sistema SHALL conservar el histórico de asignaciones. Una asignación vencida NO se borra: permanece consultable para auditoría y para clonado entre períodos. Eliminar una asignación es soft delete (nunca borrado físico). Vencer una asignación se hace seteando `hasta` en el pasado, no eliminándola.

#### Scenario: Asignación vencida se conserva
- **WHEN** una asignación llega a su fecha `hasta`
- **THEN** la asignación sigue existiendo en la base de datos y es consultable en el histórico

#### Scenario: Eliminar asignación es soft delete
- **WHEN** un usuario con permiso `equipos:asignar` envía DELETE `/api/v1/asignaciones/{id}`
- **THEN** el sistema setea `deleted_at` y retorna 204; el registro no se borra físicamente

#### Scenario: Multi-rol del mismo usuario
- **WHEN** un usuario tiene una asignación vigente como PROFESOR en una materia y otra como COORDINADOR en una carrera
- **THEN** ambas asignaciones coexisten y se listan para ese usuario

#### Scenario: Jerarquía mediante responsable_id
- **WHEN** se crea una asignación con `responsable_id` apuntando a otro usuario del tenant
- **THEN** el sistema registra la relación de supervisión y la expone al consultar la asignación

---

### Requirement: Schemas de asignación con extra forbid

El sistema SHALL validar los DTO de request de asignaciones con Pydantic v2 y `extra='forbid'`, rechazando campos no declarados.

#### Scenario: Campo no declarado rechazado
- **WHEN** una petición de creación de asignación incluye un campo no declarado en el schema
- **THEN** el sistema retorna 422 Unprocessable Entity
