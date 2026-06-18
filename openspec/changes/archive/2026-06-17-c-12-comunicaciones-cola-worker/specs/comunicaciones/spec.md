## ADDED Requirements

### Requirement: Ciclo de vida de un mensaje saliente
El sistema SHALL gestionar cada `Comunicacion` a través de una máquina de estados estricta: Pendiente → Enviando → Enviado | Error | Cancelado. Las transiciones inversas NO están permitidas.

#### Scenario: Transición válida Pendiente → Enviando
- **WHEN** el worker toma un mensaje en estado Pendiente (aprobado o no requiere aprobación)
- **THEN** el estado pasa a Enviando y `enviado_at` permanece nulo hasta confirmación

#### Scenario: Transición válida Enviando → Enviado
- **WHEN** el SMTP confirma entrega del mensaje en estado Enviando
- **THEN** el estado pasa a Enviado y `enviado_at` se registra con la fecha-hora actual

#### Scenario: Transición válida Enviando → Error
- **WHEN** el SMTP falla durante el despacho de un mensaje en estado Enviando
- **THEN** el estado pasa a Error y `enviado_at` permanece nulo

#### Scenario: Transición válida Pendiente → Cancelado
- **WHEN** un usuario con `comunicacion:enviar` cancela un mensaje en estado Pendiente
- **THEN** el estado pasa a Cancelado

#### Scenario: Transición inválida rechazada
- **WHEN** se intenta cancelar un mensaje en estado Enviado o Enviando
- **THEN** el sistema retorna 422 y no modifica el estado

---

### Requirement: Preview obligatorio antes de envío
El sistema SHALL proveer un endpoint de preview que renderice el asunto y cuerpo con variables de sustitución resueltas, SIN persistir ni encolar ningún mensaje.

#### Scenario: Preview exitoso con variables
- **WHEN** se llama `POST /api/v1/comunicaciones/preview` con asunto, cuerpo, y contexto del alumno/materia
- **THEN** el sistema retorna asunto y cuerpo con todas las variables `{{...}}` reemplazadas por sus valores

#### Scenario: Variable no reconocida en preview
- **WHEN** el cuerpo contiene una variable desconocida como `{{foo.bar}}`
- **THEN** el sistema retorna el asunto/cuerpo con la variable literal y un campo `warnings` listando las variables no resueltas

#### Scenario: Preview no persiste datos
- **WHEN** se llama al endpoint de preview
- **THEN** ningún registro de `Comunicacion` es creado en la base de datos

---

### Requirement: Envío individual con encolado
El sistema SHALL permitir a un usuario con `comunicacion:enviar` encolar un mensaje a un único destinatario.

#### Scenario: Encolado exitoso individual
- **WHEN** se llama `POST /api/v1/comunicaciones/enviar` con un único destinatario y `lote_id=None`
- **THEN** se crea un registro `Comunicacion` con estado Pendiente, `destinatario` cifrado AES-256, y `enviado_por` tomado del JWT

#### Scenario: Sin permiso comunicacion:enviar
- **WHEN** un usuario sin permiso `comunicacion:enviar` intenta encolar un mensaje
- **THEN** el sistema retorna 403

---

### Requirement: Envío masivo con lote
El sistema SHALL agrupar múltiples mensajes bajo un mismo `lote_id` cuando se envían en la misma operación masiva.

#### Scenario: Encolado masivo exitoso
- **WHEN** se llama `POST /api/v1/comunicaciones/enviar` con N destinatarios (N > 1)
- **THEN** se crean N registros `Comunicacion` con el mismo `lote_id`, todos en estado Pendiente

#### Scenario: Lote vacío rechazado
- **WHEN** se llama al endpoint de envío con lista de destinatarios vacía
- **THEN** el sistema retorna 422

---

### Requirement: Aprobación de lote cuando tenant lo requiere
El sistema SHALL retener los mensajes masivos en estado Pendiente hasta aprobación explícita cuando `requiere_aprobacion=True` en el tenant.

#### Scenario: Lote pendiente sin aprobación
- **WHEN** `requiere_aprobacion=True` y se encola un lote masivo
- **THEN** los mensajes permanecen en estado Pendiente y el worker NO los procesa hasta recibir aprobación

#### Scenario: Aprobación de lote completo
- **WHEN** un usuario con `comunicacion:aprobar` llama `POST /api/v1/comunicaciones/lotes/{lote_id}/aprobar`
- **THEN** todos los mensajes Pendiente del lote quedan marcados como aprobados (`aprobado_at` registrado) y el worker los procesa en el próximo ciclo

#### Scenario: Rechazo de lote completo
- **WHEN** un usuario con `comunicacion:aprobar` llama `POST /api/v1/comunicaciones/lotes/{lote_id}/cancelar`
- **THEN** todos los mensajes Pendiente del lote pasan a estado Cancelado

#### Scenario: Envío individual sin aprobación requerida
- **WHEN** `requiere_aprobacion=True` y se encola un mensaje individual (sin lote)
- **THEN** el worker procesa el mensaje sin esperar aprobación

#### Scenario: Sin permiso comunicacion:aprobar
- **WHEN** un usuario sin permiso `comunicacion:aprobar` intenta aprobar un lote
- **THEN** el sistema retorna 403

---

### Requirement: Cancelación individual de mensaje pendiente
El sistema SHALL permitir cancelar un mensaje individual en estado Pendiente.

#### Scenario: Cancelación exitosa
- **WHEN** un usuario con `comunicacion:enviar` llama `POST /api/v1/comunicaciones/{id}/cancelar` sobre un mensaje Pendiente
- **THEN** el mensaje pasa a estado Cancelado

#### Scenario: Cancelación de mensaje no Pendiente
- **WHEN** se intenta cancelar un mensaje en estado Enviando, Enviado o Error
- **THEN** el sistema retorna 422

---

### Requirement: Listado de comunicaciones con filtros
El sistema SHALL exponer un endpoint `GET /api/v1/comunicaciones` que retorne mensajes del tenant autenticado, con filtros por estado, lote_id, materia y rango de fechas.

#### Scenario: Listado scoped por tenant
- **WHEN** un usuario con `comunicacion:ver` consulta el listado
- **THEN** solo se retornan mensajes del tenant del usuario autenticado (nunca de otros tenants)

#### Scenario: Campo destinatario enmascarado en respuesta
- **WHEN** se retorna un listado de mensajes
- **THEN** el campo `destinatario` aparece enmascarado (`****@dominio.com`) y nunca en texto plano

#### Scenario: Filtro por estado
- **WHEN** se llama con `?estado=Pendiente`
- **THEN** solo se retornan mensajes en estado Pendiente

---

### Requirement: Worker despacha mensajes aprobados
El sistema SHALL ejecutar un worker asíncrono que procese mensajes en estado Pendiente aprobados (o sin requisito de aprobación).

#### Scenario: Despacho exitoso
- **WHEN** el worker encuentra un mensaje Pendiente elegible
- **THEN** transiciona a Enviando, despacha por SMTP, transiciona a Enviado, registra `enviado_at`

#### Scenario: Fallo de SMTP
- **WHEN** el SMTP lanza excepción durante el despacho
- **THEN** el mensaje pasa a estado Error (el worker no hace crash, continúa con el siguiente)

#### Scenario: Recuperación de estado Enviando huérfano al arrancar
- **WHEN** el worker arranca y hay mensajes en estado Enviando con `enviado_at IS NULL` y antigüedad > 5 minutos
- **THEN** el worker los resetea a estado Error antes de comenzar el loop de polling

---

### Requirement: Audit log de envío
El sistema SHALL registrar un evento `COMUNICACION_ENVIAR` en el audit log cada vez que un mensaje transiciona a estado Enviado.

#### Scenario: Audit registrado en envío exitoso
- **WHEN** el worker transiciona un mensaje a estado Enviado
- **THEN** se crea un registro de AuditLog con `accion=COMUNICACION_ENVIAR`, `usuario_id=enviado_por`, `tenant_id`, y referencia al `comunicacion_id`

---

### Requirement: Destinatario cifrado en reposo
El sistema SHALL almacenar el campo `destinatario` (email del alumno) cifrado con AES-256 en la tabla `comunicacion`.

#### Scenario: Almacenamiento cifrado
- **WHEN** se persiste un mensaje
- **THEN** el valor raw en la columna `destinatario` de la DB es el texto cifrado, no el email en claro

#### Scenario: Descifrado transparente en el worker
- **WHEN** el worker lee un mensaje para despacharlo
- **THEN** el email se descifra internamente y se pasa al cliente SMTP; nunca se loguea en texto plano
