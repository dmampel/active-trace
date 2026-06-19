## ADDED Requirements

### Requirement: Crear aviso institucional
Un usuario con permiso `avisos:publicar` (COORDINADOR / ADMIN) SHALL poder crear un aviso con los campos: título, cuerpo enriquecido, alcance (Global | PorMateria | PorCohorte | PorRol), contexto opcional (materia_id, cohorte_id, rol_destino), severidad (Info | Advertencia | Crítico), ventana de visibilidad (inicio_en, fin_en), orden de prioridad, flag activo y flag requiere_ack.

#### Scenario: Crear aviso global exitosamente
- **WHEN** un COORDINADOR envía POST /api/avisos/ con alcance=Global, titulo, cuerpo, inicio_en y fin_en válidos
- **THEN** el sistema persiste el aviso con tenant_id del usuario autenticado y devuelve 201 con el aviso creado

#### Scenario: Crear aviso por cohorte sin cohorte_id falla
- **WHEN** un ADMIN envía POST /api/avisos/ con alcance=PorCohorte y cohorte_id ausente
- **THEN** el sistema devuelve 422 con error de validación en el campo cohorte_id

#### Scenario: Usuario sin permiso avisos:publicar no puede crear aviso
- **WHEN** un PROFESOR envía POST /api/avisos/
- **THEN** el sistema devuelve 403

#### Scenario: Crear aviso PorRol sin rol_destino falla
- **WHEN** un COORDINADOR envía POST /api/avisos/ con alcance=PorRol y rol_destino ausente
- **THEN** el sistema devuelve 422 con error de validación en rol_destino

---

### Requirement: Listar y consultar avisos (gestión)
Un usuario con permiso `avisos:publicar` SHALL poder listar todos los avisos del tenant (incluyendo inactivos y vencidos) y consultar el detalle de cualquier aviso. El listado incluye contadores derivados: total_vistas y total_acks.

#### Scenario: Listar avisos del tenant
- **WHEN** un COORDINADOR envía GET /api/avisos/
- **THEN** el sistema devuelve 200 con todos los avisos del tenant (activos e inactivos), ordenados por orden ASC

#### Scenario: Detalle de aviso incluye contadores
- **WHEN** un ADMIN envía GET /api/avisos/{id} de un aviso existente
- **THEN** el sistema devuelve 200 con el aviso y los campos total_vistas y total_acks derivados de AcknowledgmentAviso

---

### Requirement: Modificar y desactivar aviso
Un usuario con permiso `avisos:publicar` SHALL poder actualizar cualquier campo de un aviso existente del tenant, incluyendo desactivarlo (activo=false).

#### Scenario: Actualizar título de aviso
- **WHEN** un COORDINADOR envía PATCH /api/avisos/{id} con nuevo titulo
- **THEN** el sistema actualiza el aviso y devuelve 200 con el aviso modificado

#### Scenario: Desactivar aviso
- **WHEN** un ADMIN envía PATCH /api/avisos/{id} con activo=false
- **THEN** el sistema marca activo=false y el aviso deja de aparecer en el feed de destinatarios

#### Scenario: No puede modificar aviso de otro tenant
- **WHEN** un COORDINADOR envía PATCH /api/avisos/{id} donde el aviso pertenece a otro tenant
- **THEN** el sistema devuelve 404

---

### Requirement: Eliminar aviso (soft delete)
Un usuario con permiso `avisos:publicar` SHALL poder eliminar un aviso del tenant con soft delete.

#### Scenario: Eliminar aviso exitosamente
- **WHEN** un ADMIN envía DELETE /api/avisos/{id}
- **THEN** el sistema aplica soft delete y devuelve 204; el aviso ya no aparece en ningún feed

---

### Requirement: Feed de "mis avisos" filtrado por audiencia y vigencia
Cualquier usuario autenticado SHALL poder obtener el listado de avisos que le corresponden según su rol, alcance y contexto (materias y cohortes de sus asignaciones activas), dentro de la ventana de vigencia activa del aviso.

#### Scenario: Feed excluye avisos fuera de ventana de vigencia
- **WHEN** un PROFESOR envía GET /api/avisos/mis-avisos y existen avisos con fin_en < NOW()
- **THEN** el sistema devuelve solo los avisos cuyo inicio_en <= NOW() <= fin_en (o fin_en IS NULL)

#### Scenario: Feed excluye avisos inactivos
- **WHEN** un ALUMNO envía GET /api/avisos/mis-avisos y existe un aviso activo=false
- **THEN** ese aviso NO aparece en la respuesta

#### Scenario: Aviso global visible para todos los roles
- **WHEN** cualquier usuario autenticado envía GET /api/avisos/mis-avisos y existe un aviso activo con alcance=Global dentro de vigencia
- **THEN** ese aviso aparece en el feed del usuario independientemente de su rol

#### Scenario: Aviso PorRol visible solo para el rol destinatario
- **WHEN** un TUTOR envía GET /api/avisos/mis-avisos y existe un aviso activo con alcance=PorRol y rol_destino=PROFESOR
- **THEN** ese aviso NO aparece en el feed del TUTOR

#### Scenario: Aviso PorCohorte visible solo para usuarios de esa cohorte
- **WHEN** un PROFESOR con asignación en cohorte A envía GET /api/avisos/mis-avisos y existe un aviso con alcance=PorCohorte y cohorte_id=B
- **THEN** ese aviso NO aparece en el feed del PROFESOR

#### Scenario: Feed ordenado por prioridad
- **WHEN** existen múltiples avisos activos y vigentes para el usuario
- **THEN** el feed los devuelve ordenados por orden ASC, luego inicio_en DESC

---

### Requirement: Confirmación de lectura (acknowledgment)
Cualquier usuario autenticado destinatario de un aviso SHALL poder confirmar su lectura vía POST /api/avisos/{id}/ack. La confirmación es idempotente. Si requiere_ack=true, el aviso deja de aparecer en el feed del usuario tras confirmar.

#### Scenario: Confirmar lectura de aviso que requiere ack
- **WHEN** un ALUMNO envía POST /api/avisos/{id}/ack en un aviso con requiere_ack=true
- **THEN** el sistema registra AcknowledgmentAviso(aviso_id, usuario_id, confirmado_at) y devuelve 200

#### Scenario: ACK idempotente no falla en segundo intento
- **WHEN** un usuario envía POST /api/avisos/{id}/ack en un aviso que ya confirmó
- **THEN** el sistema devuelve 200 sin crear duplicado

#### Scenario: Aviso con requiere_ack desaparece del feed tras confirmar
- **WHEN** un usuario confirma lectura de un aviso con requiere_ack=true y luego llama GET /api/avisos/mis-avisos
- **THEN** ese aviso no aparece en el feed del usuario

#### Scenario: Aviso sin requiere_ack sigue visible tras confirmar
- **WHEN** un usuario confirma lectura de un aviso con requiere_ack=false y luego llama GET /api/avisos/mis-avisos
- **THEN** ese aviso sigue apareciendo en el feed del usuario

#### Scenario: No puede confirmar aviso de otro tenant
- **WHEN** un usuario envía POST /api/avisos/{id}/ack donde el aviso pertenece a otro tenant
- **THEN** el sistema devuelve 404

---

### Requirement: Contadores derivados de acknowledgment
El sistema SHALL exponer total_vistas (usuarios únicos que confirmaron) y total_acks (mismo dato — en este modelo, un ack implica vista) derivados de AcknowledgmentAviso, sin campos denormalizados en la tabla aviso.

#### Scenario: Contador refleja acks reales
- **WHEN** tres usuarios distintos confirman el mismo aviso y un ADMIN consulta GET /api/avisos/{id}
- **THEN** total_acks = 3 y total_vistas = 3

#### Scenario: Contador no cambia por ack idempotente
- **WHEN** el mismo usuario confirma el mismo aviso dos veces y un ADMIN consulta GET /api/avisos/{id}
- **THEN** total_acks = 1 (un único registro en AcknowledgmentAviso)
