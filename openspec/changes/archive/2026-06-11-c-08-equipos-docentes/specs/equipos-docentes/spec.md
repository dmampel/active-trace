## ADDED Requirements

### Requirement: Vista propia del docente (mis-asignaciones)

El sistema SHALL exponer `GET /api/v1/equipos/mis-asignaciones` que retorna las asignaciones activas del usuario autenticado dentro del tenant, con filtros opcionales por `estado_vigencia`, `materia_id`, `rol`, `carrera_id` y `cohorte_id`. El resultado MUST incluir nombre de materia, carrera, cohorte y el `estado_vigencia` derivado.

#### Scenario: Docente ve sus asignaciones vigentes
- **WHEN** un usuario PROFESOR autenticado solicita `GET /api/v1/equipos/mis-asignaciones`
- **THEN** el sistema retorna 200 con la lista de asignaciones no eliminadas donde `usuario_id` coincide con el JWT, enriquecidas con nombre de materia/carrera/cohorte y estado_vigencia derivado

#### Scenario: Filtro por rol
- **WHEN** el usuario solicita `GET /api/v1/equipos/mis-asignaciones?rol=TUTOR`
- **THEN** el sistema retorna solo las asignaciones con `rol = TUTOR` del usuario autenticado

#### Scenario: Sin asignaciones retorna lista vacía
- **WHEN** el usuario autenticado no tiene asignaciones activas
- **THEN** el sistema retorna 200 con lista vacía `[]`

---

### Requirement: Búsqueda asistida de usuarios para asignación masiva

El sistema SHALL exponer `GET /api/v1/equipos/usuarios/buscar?q=<term>&limit=<n>` que busca usuarios del tenant por nombre o apellido usando coincidencia parcial (ILIKE). Requiere permiso `equipos:manage`. El `limit` máximo es 50; por defecto 20.

#### Scenario: Búsqueda retorna coincidencias
- **WHEN** un usuario con permiso `equipos:manage` solicita `GET /api/v1/equipos/usuarios/buscar?q=garcia`
- **THEN** el sistema retorna usuarios del tenant cuyo `nombre` o `apellido` contiene "garcia" (case-insensitive), con campos `id`, `nombre`, `apellido`, `legajo`

#### Scenario: Sin coincidencias retorna lista vacía
- **WHEN** el término de búsqueda no coincide con ningún usuario del tenant
- **THEN** el sistema retorna 200 con lista vacía

#### Scenario: Sin permiso rechazado
- **WHEN** un usuario sin permiso `equipos:manage` llama al endpoint de búsqueda
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Asignación masiva de docentes

El sistema SHALL exponer `POST /api/v1/equipos/masiva` que acepta una lista de `usuario_ids` y un contexto de destino (`materia_id`, `carrera_id`, `cohorte_id`, `rol`, `desde`, `hasta?`), y crea todas las asignaciones en una sola operación. Requiere permiso `equipos:manage`. Todos los IDs de contexto MUST pertenecer al tenant del autenticado. El sistema MUST registrar un evento de auditoría `ASIGNACION_MASIVA_CREAR` con el count de asignaciones creadas.

#### Scenario: Asignación masiva exitosa
- **WHEN** un usuario con permiso `equipos:manage` envía POST con lista de `usuario_ids` y contexto válido del tenant
- **THEN** el sistema crea una asignación por cada usuario_id, retorna 201 con `{ "creadas": N }` y registra `ASIGNACION_MASIVA_CREAR` en auditoría

#### Scenario: Contexto de otro tenant rechazado
- **WHEN** algún ID de contexto (`materia_id`, `carrera_id`, `cohorte_id`) pertenece a otro tenant
- **THEN** el sistema retorna 422 y no crea ninguna asignación

#### Scenario: Lista de usuarios vacía rechazada
- **WHEN** se envía `usuario_ids: []`
- **THEN** el sistema retorna 422 Unprocessable Entity

---

### Requirement: Clonar equipo docente entre períodos

El sistema SHALL exponer `POST /api/v1/equipos/clonar` que duplica todas las asignaciones vigentes de un equipo origen (`materia_id?`, `carrera_id?`, `cohorte_id` origen) hacia un destino (al menos `cohorte_id` destino distinto del origen). Requiere permiso `equipos:manage`. Solo se clonan asignaciones no eliminadas y vigentes (hasta IS NULL o hasta >= hoy). Las asignaciones que ya existen en el destino (mismo usuario+rol+contexto) se omiten. El sistema MUST registrar `ASIGNACION_CLONAR` en auditoría.

#### Scenario: Clonado exitoso
- **WHEN** un usuario con permiso `equipos:manage` envía POST con origen y destino válidos del tenant
- **THEN** el sistema crea copias de las asignaciones vigentes hacia el destino, retorna 201 con `{ "clonadas": N, "omitidas": M }` y registra `ASIGNACION_CLONAR`

#### Scenario: Duplicado omitido silenciosamente
- **WHEN** ya existe una asignación idéntica (mismo usuario+rol+contexto) en el destino
- **THEN** esa asignación se omite y se reporta en el campo `omitidas` del response

#### Scenario: Origen con destino igual rechazado
- **WHEN** el equipo origen y el destino son idénticos
- **THEN** el sistema retorna 422 Unprocessable Entity

#### Scenario: Sin asignaciones vigentes en origen
- **WHEN** el equipo origen no tiene asignaciones vigentes
- **THEN** el sistema retorna 200 con `{ "clonadas": 0, "omitidas": 0 }`

---

### Requirement: Modificar vigencia general del equipo

El sistema SHALL exponer `PATCH /api/v1/equipos/vigencia` que actualiza `desde` y/o `hasta` de todas las asignaciones no eliminadas de un equipo (identificado por `materia_id?`, `carrera_id?`, `cohorte_id`). Requiere permiso `equipos:manage`. MUST registrar `ASIGNACION_VIGENCIA_BULK` en auditoría.

#### Scenario: Actualización de vigencia exitosa
- **WHEN** un usuario con permiso `equipos:manage` envía PATCH con equipo identificado y nuevas fechas
- **THEN** el sistema actualiza `desde`/`hasta` de todas las asignaciones del equipo, retorna 200 con `{ "actualizadas": N }` y registra `ASIGNACION_VIGENCIA_BULK`

#### Scenario: Ninguna asignación en el equipo
- **WHEN** no hay asignaciones para el equipo especificado
- **THEN** el sistema retorna 200 con `{ "actualizadas": 0 }`

---

### Requirement: Exportar equipo docente en CSV

El sistema SHALL exponer `GET /api/v1/equipos/exportar` que retorna un archivo CSV descargable con todas las asignaciones no eliminadas del tenant, con columnas: `nombre`, `apellido`, `legajo`, `rol`, `materia`, `carrera`, `cohorte`, `desde`, `hasta`, `estado_vigencia`. Requiere permiso `equipos:export`.

#### Scenario: Export CSV exitoso
- **WHEN** un usuario con permiso `equipos:export` solicita `GET /api/v1/equipos/exportar`
- **THEN** el sistema retorna `Content-Type: text/csv` con `Content-Disposition: attachment; filename="equipo.csv"` y el contenido CSV completo del tenant

#### Scenario: Sin permiso rechazado
- **WHEN** un usuario sin permiso `equipos:export` solicita el export
- **THEN** el sistema retorna 403 Forbidden
