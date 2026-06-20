## ADDED Requirements

### Requirement: ABM de avisos del sistema
El sistema SHALL permitir al COORDINADOR y ADMIN crear, editar, activar/desactivar y eliminar (soft-delete) avisos. Cada aviso DEBE configurar: alcance (global / materia / cohorte), roles destinatarios, severidad, contenido (título + cuerpo), ventana de visibilidad (fecha inicio y fin), orden de prioridad y si requiere acknowledgment.

#### Scenario: Crear aviso con alcance global
- **WHEN** el coordinador completa el formulario con alcance "global" y publica
- **THEN** el aviso queda activo y aparece en la lista con su estado y vigencia

#### Scenario: Scope "materia" exige seleccionar materia
- **WHEN** el usuario selecciona alcance "materia" en el formulario
- **THEN** el selector de materia se vuelve visible y obligatorio; el formulario no puede enviarse sin él

#### Scenario: Scope "cohorte" exige materia Y cohorte
- **WHEN** el usuario selecciona alcance "cohorte"
- **THEN** aparecen selectores de materia y cohorte, ambos obligatorios para poder enviar

#### Scenario: Editar aviso existente
- **WHEN** el coordinador edita un aviso y guarda
- **THEN** los cambios se persisten y la lista se actualiza sin recargar la página

#### Scenario: Aviso fuera de vigencia no aparece en lista activa
- **WHEN** un aviso supera su fecha "hasta"
- **THEN** desaparece de la lista de avisos activos aunque siga existiendo en el historial

---

### Requirement: Vista de confirmaciones de lectura (acknowledgment)
El sistema SHALL mostrar al publicador del aviso cuántos y cuáles usuarios confirmaron la lectura de un aviso con `require_ack = true`.

#### Scenario: Ver confirmaciones de un aviso
- **WHEN** el coordinador accede a `/avisos/:id/confirmaciones`
- **THEN** se muestra la lista de usuarios que confirmaron, con fecha/hora de confirmación, y el total pendiente

#### Scenario: Aviso sin acknowledgment no muestra sección de confirmaciones
- **WHEN** el aviso tiene `require_ack = false`
- **THEN** la ruta de confirmaciones redirige o muestra un mensaje indicando que el aviso no requiere confirmación

---

### Requirement: Vista de mis tareas (docente)
El sistema SHALL mostrar al usuario autenticado sus tareas asignadas, con estado, materia, asignador y comentarios del hilo. El docente PUEDE actualizar el estado y agregar comentarios.

#### Scenario: Docente ve sus tareas abiertas
- **WHEN** el usuario navega a `/tareas`
- **THEN** se muestra la lista de tareas asignadas a él ordenadas por estado (Abierta primero) y fecha

#### Scenario: Agregar comentario a una tarea
- **WHEN** el docente escribe un comentario y lo envía
- **THEN** el comentario aparece al final del hilo de la tarea sin recargar la página

#### Scenario: Cambiar estado de tarea
- **WHEN** el docente selecciona "En progreso" o "Completada" en el selector de estado
- **THEN** el estado se actualiza en el servidor y la tarjeta refleja el nuevo estado inmediatamente

---

### Requirement: Administración de tareas del tenant (coordinador)
El sistema SHALL permitir al COORDINADOR y ADMIN ver todas las tareas del tenant, filtrar por docente asignado, asignador, materia y estado, cambiar el estado de cualquier tarea y agregar comentarios.

#### Scenario: Vista global de tareas con filtros
- **WHEN** el coordinador accede a `/coordinacion/tareas`
- **THEN** se muestra la tabla completa de tareas del tenant con columnas: materia, asignado a, asignado por, estado, última actualización

#### Scenario: Filtrar tareas por estado y docente
- **WHEN** el coordinador aplica filtro "Abierta" y selecciona un docente
- **THEN** la tabla muestra solo las tareas abiertas de ese docente

#### Scenario: Coordinador cambia estado y agrega observación
- **WHEN** el coordinador cambia el estado a "Rechazada" y agrega una observación
- **THEN** el nuevo estado y el comentario quedan registrados en el hilo de la tarea

---

### Requirement: Cola de aprobación de comunicaciones (coordinador)
El sistema SHALL mostrar al rol con permiso `comunicacion:aprobar` los mensajes en estado Pendiente, y permitir aprobarlos o cancelarlos individualmente o en lote.

#### Scenario: Ver mensajes pendientes de aprobación
- **WHEN** el coordinador accede a `/coordinacion/comunicaciones/aprobacion`
- **THEN** se muestra la lista de mensajes Pendientes del tenant con asunto, destinatario y docente emisor

#### Scenario: Aprobar lote de mensajes
- **WHEN** el coordinador selecciona todos los mensajes y hace click en "Aprobar lote"
- **THEN** los mensajes pasan a estado Enviando y la lista se actualiza (polling automático cada 5 s mientras haya pendientes)

#### Scenario: Cancelar mensaje individual
- **WHEN** el coordinador cancela un mensaje específico
- **THEN** ese mensaje pasa a estado Cancelado y desaparece de la cola de pendientes

#### Scenario: Sin mensajes pendientes
- **WHEN** no hay mensajes en estado Pendiente
- **THEN** la pantalla muestra un estado vacío con mensaje informativo; no se activa polling
