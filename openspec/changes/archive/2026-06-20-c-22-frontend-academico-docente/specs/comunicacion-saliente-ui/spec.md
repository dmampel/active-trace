## ADDED Requirements

### Requirement: Selección de destinatarios y preview de mensaje
El sistema SHALL proveer en `/comision/:comisionId/comunicacion` una interfaz donde el PROFESOR seleccione alumnos atrasados de la tabla y pueda previsualizar el mensaje que recibirá cada destinatario antes de enviar. La selección SHALL soportar seleccionar todos con un checkbox de cabecera.

#### Scenario: Checkbox de cabecera selecciona/deselecciona todos
- **WHEN** el usuario hace clic en el checkbox de la cabecera de la tabla
- **THEN** todos los alumnos listados quedan seleccionados o deseleccionados según el estado previo

#### Scenario: Botón "Previsualizar" habilitado solo con al menos un destinatario
- **WHEN** no hay ningún alumno seleccionado
- **THEN** el botón "Previsualizar mensaje" aparece deshabilitado

#### Scenario: Modal de preview muestra mensaje interpolado del primer destinatario
- **WHEN** el usuario hace clic en "Previsualizar mensaje" con al menos un destinatario seleccionado
- **THEN** se abre un modal con el asunto y el cuerpo del mensaje personalizado con los datos del primer destinatario de la lista

#### Scenario: Modal de preview se cierra sin enviar
- **WHEN** el usuario cierra el modal de preview
- **THEN** la selección de destinatarios permanece intacta y no se envía ningún mensaje

### Requirement: Envío masivo a la cola de comunicaciones
El sistema SHALL permitir confirmar el envío desde el modal de preview o desde un botón "Enviar" en la página. El envío SHALL crear un registro por destinatario en la cola con estado inicial Pendiente.

#### Scenario: Confirmar envío desde el modal crea mensajes en cola
- **WHEN** el usuario hace clic en "Confirmar envío" dentro del modal de preview
- **THEN** el sistema envía la request al backend con la lista de destinatarios seleccionados; al recibir 200, cierra el modal y navega a la vista de tracking

#### Scenario: Envío fallido muestra error sin abandonar la página
- **WHEN** el backend responde con error 4xx/5xx al intentar encolar los mensajes
- **THEN** el modal permanece abierto y muestra el mensaje de error retornado por el backend

### Requirement: Tracking de estado en tiempo real
El sistema SHALL mostrar una tabla de seguimiento de mensajes enviados con columnas: destinatario, estado actual y timestamp del último cambio. La tabla SHALL actualizarse automáticamente mientras haya mensajes en estado Pendiente o Enviando.

#### Scenario: Polling activo mientras hay mensajes en tránsito
- **WHEN** la tabla contiene al menos un mensaje en estado Pendiente o Enviando
- **THEN** la página refresca los estados automáticamente cada 3 segundos sin intervención del usuario

#### Scenario: Polling se detiene cuando todos los mensajes llegan a estado final
- **WHEN** todos los mensajes están en estado OK, Fallido o Cancelado
- **THEN** el polling se detiene y la tabla deja de actualizarse automáticamente

#### Scenario: Estado de cada mensaje se refleja con indicador visual
- **WHEN** la tabla de tracking está visible
- **THEN** cada fila muestra un badge de color diferente por estado: Pendiente (gris), Enviando (amarillo), OK (verde), Fallido (rojo), Cancelado (naranja)

#### Scenario: Tabla de tracking muestra mensaje cuando no hay envíos previos
- **WHEN** el usuario accede a la página de comunicación sin envíos previos en la comisión
- **THEN** se muestra el estado vacío "Aún no hay mensajes enviados para esta comisión"

### Requirement: Sin modificación del estado desde frontend
El sistema NO SHALL proveer controles para cambiar el estado de un mensaje individual desde el frontend del PROFESOR. Los estados son de solo lectura en esta vista. La aprobación de envíos masivos corresponde a COORDINADOR (C-23).

#### Scenario: Tabla de tracking es de solo lectura para PROFESOR
- **WHEN** el PROFESOR visualiza la tabla de tracking
- **THEN** no existe ningún botón ni acción que permita cambiar el estado de un mensaje individual
