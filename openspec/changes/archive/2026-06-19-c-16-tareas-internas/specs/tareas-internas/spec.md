## ADDED Requirements

### Requirement: Alta de tarea interna
El sistema SHALL permitir a un usuario con permiso `tareas:gestionar` crear una tarea asignándola a otro usuario del mismo tenant. La tarea nace en estado `pendiente`. Los campos `materia_id` y `contexto_id` son opcionales.

#### Scenario: Alta exitosa de tarea
- **WHEN** un COORDINADOR crea una tarea con `asignado_a` válido, `descripcion` no vacía y `tenant_id` resuelto desde la sesión
- **THEN** el sistema persiste la tarea con estado `pendiente`, `asignado_por` = usuario de sesión, y retorna `201` con el recurso creado

#### Scenario: Alta rechazada sin permiso
- **WHEN** un usuario sin el permiso `tareas:gestionar` intenta crear una tarea
- **THEN** el sistema retorna `403 Forbidden`

#### Scenario: Alta rechazada con `asignado_a` de otro tenant
- **WHEN** el `asignado_a` referencia un usuario que no pertenece al tenant de sesión
- **THEN** el sistema retorna `422 Unprocessable Entity`

---

### Requirement: Vista de mis tareas
El sistema SHALL proveer a cada usuario con permiso `tareas:gestionar` una vista de las tareas que le fueron asignadas (`asignado_a` = usuario de sesión), filtradas por tenant. Soporta filtro opcional por `estado`.

#### Scenario: Docente ve sus tareas pendientes
- **WHEN** un PROFESOR consulta `GET /api/tareas/mis-tareas?estado=pendiente`
- **THEN** el sistema retorna solo las tareas donde `asignado_a` es el usuario de sesión y `estado = pendiente`, dentro de su tenant

#### Scenario: Vista vacía sin tareas asignadas
- **WHEN** un usuario no tiene tareas asignadas
- **THEN** el sistema retorna `200` con lista vacía

---

### Requirement: Transición de estado de tarea
El sistema SHALL permitir cambiar el estado de una tarea siguiendo las transiciones válidas. Transiciones permitidas: `pendiente → en_progreso | cancelada`; `en_progreso → resuelta | cancelada | pendiente`. Los estados `resuelta` y `cancelada` son terminales.

#### Scenario: Transición válida a en_progreso
- **WHEN** el asignado (o COORDINADOR) cambia estado de `pendiente` a `en_progreso`
- **THEN** el sistema persiste el nuevo estado y retorna `200` con la tarea actualizada

#### Scenario: Transición inválida desde estado terminal
- **WHEN** cualquier usuario intenta cambiar el estado de una tarea `resuelta`
- **THEN** el sistema retorna `422 Unprocessable Entity` con mensaje descriptivo

#### Scenario: Solo involucrados o coordinación pueden transicionar
- **WHEN** un usuario que no es `asignado_a`, `asignado_por` ni COORDINADOR/ADMIN intenta cambiar el estado
- **THEN** el sistema retorna `403 Forbidden`

---

### Requirement: Hilo de comentarios en tarea
El sistema SHALL permitir agregar comentarios a una tarea. Los comentarios son append-only (no se editan ni eliminan). El autor queda registrado como `autor_id` resuelto desde la sesión.

#### Scenario: Comentario agregado exitosamente
- **WHEN** un usuario con permiso `tareas:gestionar` agrega un comentario a una tarea de su tenant
- **THEN** el sistema persiste el comentario con `autor_id`, `tarea_id`, `tenant_id` y `creado_at`, y retorna `201`

#### Scenario: Comentario en tarea de otro tenant rechazado
- **WHEN** el `tarea_id` pertenece a un tenant diferente al de la sesión
- **THEN** el sistema retorna `404 Not Found` (no se revela existencia cross-tenant)

#### Scenario: Listado de comentarios en orden cronológico
- **WHEN** se consultan los comentarios de una tarea
- **THEN** el sistema los retorna ordenados por `creado_at` ascendente

---

### Requirement: Administración global de tareas (coordinación)
El sistema SHALL proveer a COORDINADOR y ADMIN una vista paginada de todas las tareas del tenant con filtros por `asignado_a`, `asignado_por`, `materia_id` y `estado`.

#### Scenario: Coordinador filtra tareas por estado y docente
- **WHEN** un COORDINADOR consulta `GET /api/tareas?estado=pendiente&asignado_a=<uuid>`
- **THEN** el sistema retorna la lista paginada de tareas que cumplen los filtros, dentro del tenant

#### Scenario: Docente sin rol coordinador no accede a la vista global
- **WHEN** un PROFESOR consulta `GET /api/tareas` (sin `mis-tareas`)
- **THEN** el sistema retorna `403 Forbidden`

#### Scenario: Paginación con page y size
- **WHEN** se consulta con `page=2&size=10`
- **THEN** el sistema retorna el segundo bloque de 10 tareas y metadatos de paginación (`total`, `page`, `size`)

---

### Requirement: Multi-tenancy row-level en tareas
El sistema SHALL garantizar que ningún query sobre `Tarea` o `ComentarioTarea` retorne filas de un tenant diferente al de la sesión activa. El `tenant_id` NUNCA se acepta como parámetro de entrada.

#### Scenario: Tarea de otro tenant invisible
- **WHEN** un usuario autenticado intenta acceder a una tarea cuyo `tenant_id` no coincide con el de su sesión
- **THEN** el sistema retorna `404 Not Found`

#### Scenario: tenant_id resuelto desde JWT
- **WHEN** se crea o consulta cualquier recurso del módulo de tareas
- **THEN** el `tenant_id` se obtiene exclusivamente del JWT verificado, nunca del body ni de query params
