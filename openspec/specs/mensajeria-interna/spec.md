## ADDED Requirements

### Requirement: Modelo de hilo y mensaje interno

El sistema SHALL modelar la mensajería interna entre usuarios registrados con dos entidades nuevas, paralelas e independientes de las comunicaciones salientes a alumnos:
- `hilo_mensaje`: conversación con `id` (UUID), `tenant_id` (FK Tenant), `asunto`, `creado_por` (FK Usuario), `created_at`, `deleted_at` (soft delete).
- `mensaje_interno`: `id` (UUID), `tenant_id`, `hilo_id` (FK HiloMensaje), `autor_id` (FK Usuario), `destinatario_id` (FK Usuario), `cuerpo`, `leido` (booleano), `created_at`, `deleted_at` (soft delete).

Ambas tablas MUST incluir `tenant_id` y los repositories MUST filtrar por tenant por defecto. La eliminación SHALL ser soft delete (nunca borrado físico).

#### Scenario: Hilo y mensaje persistidos con tenant y soft delete
- **WHEN** se crea un hilo con su primer mensaje interno
- **THEN** ambos registros se persisten con el `tenant_id` del autor, `deleted_at` nulo y referencias válidas entre hilo y mensaje

#### Scenario: Eliminación es soft delete
- **WHEN** se elimina un mensaje o un hilo
- **THEN** el registro queda con `deleted_at` establecido y nunca se borra físicamente de la base

---

### Requirement: Bandeja de hilos recibidos

El sistema SHALL exponer `GET /api/v1/inbox` para listar los hilos en los que el usuario autenticado es destinatario de al menos un mensaje. La identidad MUST derivarse del JWT verificado. El listado SHALL incluir solo hilos del tenant del autenticado y MUST excluir hilos donde el usuario no participa. El endpoint requiere `inbox:usar` y es fail-closed.

#### Scenario: Listar hilos propios recibidos
- **WHEN** un usuario autenticado solicita `GET /api/v1/inbox`
- **THEN** el sistema retorna 200 con los hilos donde es destinatario, dentro de su tenant

#### Scenario: Aislamiento por usuario
- **WHEN** existe un hilo dirigido a otro usuario del mismo tenant
- **THEN** ese hilo NO aparece en el inbox del usuario que no es destinatario

#### Scenario: Aislamiento por tenant
- **WHEN** existe un hilo en otro tenant dirigido a un usuario homónimo
- **THEN** ese hilo NO aparece en el inbox del usuario del tenant actual

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `inbox:usar` solicita `GET /api/v1/inbox`
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Lectura de un hilo y marcado de leído

El sistema SHALL exponer `GET /api/v1/inbox/{hilo_id}` para que el destinatario abra un hilo y lea sus mensajes ordenados cronológicamente. Al abrir el hilo, los mensajes dirigidos al usuario autenticado SHALL marcarse `leido = true`. Solo un participante del hilo (del mismo tenant) puede leerlo; cualquier otro acceso es fail-closed.

#### Scenario: Abrir hilo marca mensajes como leídos
- **WHEN** el destinatario solicita `GET /api/v1/inbox/{hilo_id}` de un hilo propio con mensajes no leídos
- **THEN** el sistema retorna 200 con los mensajes ordenados por fecha y marca como `leido = true` los dirigidos al usuario

#### Scenario: Acceso a hilo ajeno rechazado
- **WHEN** un usuario solicita `GET /api/v1/inbox/{hilo_id}` de un hilo en el que no participa o de otro tenant
- **THEN** el sistema retorna 404 Not Found y no expone el contenido

---

### Requirement: Responder dentro de un hilo

El sistema SHALL exponer `POST /api/v1/inbox/{hilo_id}/responder` para que un participante agregue un mensaje al hilo existente. El `autor_id` MUST derivarse del JWT; el `destinatario_id` SHALL ser el otro participante del hilo. El schema de entrada (`cuerpo`) MUST usar `extra='forbid'`. Solo participantes del hilo dentro del tenant pueden responder.

#### Scenario: Responder agrega mensaje al hilo
- **WHEN** un participante envía `POST /api/v1/inbox/{hilo_id}/responder` con un `cuerpo` válido
- **THEN** el sistema crea un nuevo `mensaje_interno` en ese hilo con `autor_id` del JWT, `leido = false` para el destinatario, y retorna 201

#### Scenario: Responder en hilo ajeno rechazado
- **WHEN** un usuario que no participa del hilo intenta responder
- **THEN** el sistema retorna 404 Not Found y no crea el mensaje

#### Scenario: Cuerpo con campo no declarado rechazado
- **WHEN** la petición incluye un campo no declarado en el schema de respuesta
- **THEN** el sistema retorna 422 por `extra='forbid'`

---

### Requirement: Envío de un nuevo mensaje interno

El sistema SHALL exponer `POST /api/v1/inbox` para que un usuario autenticado inicie un nuevo hilo dirigido a otro usuario registrado del mismo tenant, con `asunto` y `cuerpo`. El `autor_id`/`creado_por` MUST derivarse del JWT. El `destinatario_id` SHALL referenciar un usuario existente y activo del mismo tenant; un destinatario de otro tenant es inválido. El schema MUST usar `extra='forbid'`.

#### Scenario: Crear nuevo hilo con primer mensaje
- **WHEN** un usuario envía `POST /api/v1/inbox` con `destinatario_id` válido del tenant, `asunto` y `cuerpo`
- **THEN** el sistema crea un `hilo_mensaje` y su primer `mensaje_interno` (`leido = false`) y retorna 201

#### Scenario: Destinatario de otro tenant rechazado
- **WHEN** un usuario envía `POST /api/v1/inbox` con un `destinatario_id` que pertenece a otro tenant
- **THEN** el sistema retorna 404/422 y no crea el hilo
