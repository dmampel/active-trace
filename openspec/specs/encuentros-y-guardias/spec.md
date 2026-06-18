## ADDED Requirements

### Requirement: Crear slot de encuentro recurrente
El sistema SHALL crear un `SlotEncuentro` recurrente y generar automáticamente todas las instancias de la serie cuando `cant_semanas > 0`. La generación calcula N fechas a partir de `fecha_inicio` con intervalos de 7 días.

#### Scenario: Slot recurrente genera N instancias
- **WHEN** PROFESOR envía POST `/api/encuentros/slots` con `cant_semanas = 4`, `fecha_inicio`, `dia_semana` y `hora`
- **THEN** el sistema crea 1 `SlotEncuentro` y 4 `InstanciaEncuentro` con estado `Programado`, fechas consecutivas cada 7 días

#### Scenario: cant_semanas excede el máximo
- **WHEN** PROFESOR envía POST con `cant_semanas = 53`
- **THEN** el sistema retorna HTTP 422 con error de validación

#### Scenario: rol sin permiso intenta crear slot
- **WHEN** ALUMNO envía POST `/api/encuentros/slots`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Crear encuentro único
El sistema SHALL crear un `SlotEncuentro` con `fecha_unica` y generar exactamente 1 `InstanciaEncuentro`.

#### Scenario: Encuentro único genera 1 instancia
- **WHEN** PROFESOR envía POST `/api/encuentros/slots` con `fecha_unica` y sin `cant_semanas`
- **THEN** el sistema crea 1 `SlotEncuentro` y 1 `InstanciaEncuentro` con la fecha especificada

#### Scenario: fecha_unica y cant_semanas mutuamente excluyentes
- **WHEN** PROFESOR envía POST con `fecha_unica` y `cant_semanas > 0` simultáneamente
- **THEN** el sistema retorna HTTP 422

---

### Requirement: Editar instancia de encuentro
El sistema SHALL permitir editar los campos `estado`, `meet_url`, `video_url` y `comentario` de una `InstanciaEncuentro` individual sin afectar al slot ni a otras instancias.

#### Scenario: Marcar encuentro como realizado con video
- **WHEN** PROFESOR envía PATCH `/api/encuentros/instancias/{id}` con `estado = "Realizado"` y `video_url`
- **THEN** solo esa instancia queda con estado `Realizado` y `video_url` registrada; las demás instancias del slot no cambian

#### Scenario: Editar instancia de otro tenant
- **WHEN** usuario autenticado intenta editar una instancia de otro `tenant_id`
- **THEN** el sistema retorna HTTP 404

---

### Requirement: Listar instancias propias
El sistema SHALL permitir a PROFESOR listar las instancias de encuentro de sus asignaciones activas, filtradas por `tenant_id`.

#### Scenario: PROFESOR lista sus encuentros
- **WHEN** PROFESOR autenticado realiza GET `/api/encuentros/slots`
- **THEN** el sistema retorna los slots del profesor junto a sus instancias, todos del tenant del usuario

---

### Requirement: Vista admin de encuentros
El sistema SHALL permitir a COORDINADOR y ADMIN ver todos los encuentros del tenant independientemente del docente creador.

#### Scenario: COORDINADOR ve todos los encuentros del tenant
- **WHEN** COORDINADOR realiza GET `/api/encuentros/admin`
- **THEN** el sistema retorna todas las instancias del tenant con su estado y datos de encuentro

#### Scenario: PROFESOR no puede acceder a vista admin
- **WHEN** PROFESOR realiza GET `/api/encuentros/admin`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Generar bloque HTML para LMS
El sistema SHALL generar un bloque HTML con el calendario de encuentros programados y realizados (con `video_url`) de una asignación, listo para embeber en el aula virtual.

#### Scenario: HTML con encuentros mixtos
- **WHEN** PROFESOR realiza GET `/api/encuentros/html-block?asignacion_id={id}`
- **THEN** el sistema retorna HTML con tabla de encuentros; los realizados muestran link al video; los programados muestran solo fecha/hora/título

#### Scenario: HTML con caracteres especiales en título
- **WHEN** el título del encuentro contiene `<script>alert(1)</script>`
- **THEN** el HTML retornado tiene los caracteres escapados (`&lt;script&gt;`)

---

### Requirement: Registrar guardia
El sistema SHALL permitir a TUTOR registrar una guardia propia con materia, carrera/cohorte, día, horario, estado y comentarios.

#### Scenario: TUTOR registra guardia exitosamente
- **WHEN** TUTOR autenticado envía POST `/api/guardias` con datos válidos de guardia
- **THEN** el sistema crea la `Guardia` con `asignacion_id` del TUTOR y retorna HTTP 201

#### Scenario: PROFESOR intenta registrar guardia
- **WHEN** PROFESOR envía POST `/api/guardias`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Consultar guardias (coordinación)
El sistema SHALL permitir a COORDINADOR y ADMIN consultar todas las guardias del tenant con filtros por materia, estado y rango de fechas.

#### Scenario: COORDINADOR consulta guardias filtradas por materia
- **WHEN** COORDINADOR realiza GET `/api/guardias?materia_id={id}`
- **THEN** el sistema retorna solo las guardias de esa materia del tenant

#### Scenario: TUTOR solo ve sus propias guardias
- **WHEN** TUTOR realiza GET `/api/guardias`
- **THEN** el sistema retorna solo las guardias de su `asignacion_id`

---

### Requirement: Exportar guardias a CSV
El sistema SHALL permitir a COORDINADOR y ADMIN exportar el listado de guardias del tenant en formato CSV mediante streaming.

#### Scenario: Export completo del tenant
- **WHEN** COORDINADOR realiza GET `/api/guardias/export`
- **THEN** el sistema retorna un archivo CSV con todas las guardias del tenant con headers `tutor, materia, carrera, cohorte, dia, horario, estado, comentarios, creada_at`

#### Scenario: TUTOR no puede exportar
- **WHEN** TUTOR realiza GET `/api/guardias/export`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Tenant isolation en encuentros y guardias
El sistema SHALL aplicar filtro de `tenant_id` en todos los queries de `SlotEncuentro`, `InstanciaEncuentro` y `Guardia` por defecto.

#### Scenario: Aislamiento entre tenants en slots
- **WHEN** un usuario de tenant A consulta slots
- **THEN** el sistema NO retorna slots de tenant B, aunque existan en la misma tabla

#### Scenario: Aislamiento entre tenants en guardias
- **WHEN** un usuario de tenant A consulta guardias
- **THEN** el sistema NO retorna guardias de tenant B
