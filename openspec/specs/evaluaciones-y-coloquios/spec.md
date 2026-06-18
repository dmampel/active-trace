## ADDED Requirements

### Requirement: Crear convocatoria de coloquio
El sistema SHALL permitir a COORDINADOR y ADMIN crear una convocatoria de evaluación oral (coloquio) definiendo materia, cohorte, nombre de instancia, días disponibles con cupos por día (JSONB).

#### Scenario: Creación exitosa
- **WHEN** COORDINADOR envía POST `/api/coloquios` con materia_id, cohorte_id, instancia, y cupos_por_dia válidos
- **THEN** el sistema crea la Evaluacion con tipo=Coloquio, retorna HTTP 201 con el recurso creado y tenant_id tomado de la sesión

#### Scenario: Falta campo obligatorio
- **WHEN** el payload omite `instancia`
- **THEN** el sistema retorna HTTP 422 sin crear la evaluación

#### Scenario: ALUMNO no puede crear convocatoria
- **WHEN** un usuario con rol ALUMNO intenta POST `/api/coloquios`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Importar alumnos habilitados a una convocatoria
El sistema SHALL permitir a COORDINADOR y ADMIN cargar la lista de alumnos habilitados (convocados) a una Evaluacion mediante una operación de upsert.

#### Scenario: Importación exitosa
- **WHEN** COORDINADOR envía POST `/api/coloquios/{id}/alumnos` con una lista de alumno_ids válidos del mismo tenant
- **THEN** el sistema hace upsert en `evaluacion_alumno` y retorna el total de convocados

#### Scenario: alumno_id de otro tenant rechazado
- **WHEN** un alumno_id pertenece a otro tenant
- **THEN** el sistema retorna HTTP 422 y no registra ningún alumno de ese lote

---

### Requirement: Reservar turno de coloquio (ALUMNO)
El sistema SHALL permitir a un ALUMNO habilitado reservar un turno en un día disponible con cupo libre, de forma atómica.

#### Scenario: Reserva exitosa con cupo disponible
- **WHEN** ALUMNO envía POST `/api/coloquios/{id}/reservar` con una fecha disponible con cupo > 0
- **THEN** el sistema decrementa el cupo del día en 1, crea ReservaEvaluacion con estado=Activa y retorna HTTP 201

#### Scenario: Reserva rechazada por cupo agotado
- **WHEN** el cupo para el día seleccionado es 0
- **THEN** el sistema retorna HTTP 409 sin modificar estado ni cupos

#### Scenario: ALUMNO no habilitado no puede reservar
- **WHEN** el alumno no está en `evaluacion_alumno` para esa convocatoria
- **THEN** el sistema retorna HTTP 403

#### Scenario: Alumno con reserva activa no puede reservar de nuevo
- **WHEN** el alumno ya tiene una ReservaEvaluacion con estado=Activa para la misma evaluación
- **THEN** el sistema retorna HTTP 409

---

### Requirement: Cancelar reserva propia (ALUMNO)
El sistema SHALL permitir a un ALUMNO cancelar su propia reserva activa, liberando el cupo.

#### Scenario: Cancelación exitosa
- **WHEN** ALUMNO envía DELETE `/api/coloquios/{evaluacion_id}/reservar` y tiene reserva Activa
- **THEN** el sistema marca la ReservaEvaluacion como Cancelada, incrementa el cupo del día en 1 y retorna HTTP 200

#### Scenario: Cancelación de reserva inexistente
- **WHEN** el alumno no tiene reserva activa para esa evaluación
- **THEN** el sistema retorna HTTP 404

---

### Requirement: Listado de convocatorias
El sistema SHALL exponer GET `/api/coloquios` con las convocatorias del tenant del usuario autenticado, incluyendo métricas operativas (convocados, reservas activas, cupos libres).

#### Scenario: COORDINADOR ve todas las convocatorias del tenant
- **WHEN** COORDINADOR realiza GET `/api/coloquios`
- **THEN** el sistema retorna todas las Evaluacion del tenant con convocados, reservas_activas y cupos_libres totales

#### Scenario: Sin convocatorias
- **WHEN** el tenant no tiene ninguna Evaluacion
- **THEN** el sistema retorna HTTP 200 con lista vacía

---

### Requirement: Panel de métricas de coloquios
El sistema SHALL exponer GET `/api/coloquios/metricas` que retorne: total de alumnos convocados (suma de evaluacion_alumno), instancias activas, reservas activas, notas registradas.

#### Scenario: Métricas con datos
- **WHEN** COORDINADOR solicita GET `/api/coloquios/metricas`
- **THEN** el sistema retorna total_convocados, instancias_activas, reservas_activas, notas_registradas calculados en tiempo real del tenant

#### Scenario: Métricas vacías (tenant sin datos)
- **WHEN** no hay evaluaciones ni reservas
- **THEN** todos los campos retornan 0

---

### Requirement: Registrar resultado de coloquio
El sistema SHALL permitir a COORDINADOR y ADMIN registrar o actualizar la nota_final de un alumno para una Evaluacion (upsert por evaluacion_id + alumno_id).

#### Scenario: Registro exitoso
- **WHEN** COORDINADOR envía POST `/api/coloquios/{id}/resultados` con alumno_id y nota_final
- **THEN** el sistema crea o actualiza ResultadoEvaluacion para ese par y retorna HTTP 201/200

#### Scenario: nota_final puede ser texto o número
- **WHEN** nota_final es "Aprobado" o "8.5"
- **THEN** ambas formas son aceptadas y almacenadas como texto

---

### Requirement: Agenda de reservas por convocatoria
El sistema SHALL exponer GET `/api/coloquios/{id}/agenda` con el listado de ReservaEvaluacion activas, agrupadas por fecha, incluyendo datos del alumno.

#### Scenario: Agenda con reservas
- **WHEN** COORDINADOR solicita GET `/api/coloquios/{id}/agenda`
- **THEN** el sistema retorna reservas agrupadas por fecha con alumno_id, nombre, apellido y estado=Activa

#### Scenario: Agenda vacía
- **WHEN** no hay reservas activas para la evaluación
- **THEN** retorna HTTP 200 con objeto vacío por fechas

---

### Requirement: Registro consolidado de resultados por convocatoria
El sistema SHALL exponer GET `/api/coloquios/{id}/resultados` con todos los ResultadoEvaluacion de la convocatoria para auditoría y cierre académico.

#### Scenario: Listado de resultados
- **WHEN** ADMIN solicita GET `/api/coloquios/{id}/resultados`
- **THEN** retorna todos los ResultadoEvaluacion de esa evaluación con alumno_id, nota_final

---

### Requirement: Gestión de fechas académicas
El sistema SHALL permitir a COORDINADOR y ADMIN crear, editar y listar FechaAcademica (parciales, TPs, coloquios) por materia × cohorte × tipo × instancia.

#### Scenario: Crear fecha académica
- **WHEN** COORDINADOR envía POST `/api/fechas-academicas` con materia_id, cohorte_id, tipo, numero, periodo, fecha, titulo
- **THEN** el sistema crea FechaAcademica con tenant_id de la sesión y retorna HTTP 201

#### Scenario: Listar fechas académicas con filtros
- **WHEN** COORDINADOR solicita GET `/api/fechas-academicas?materia_id=X&cohorte_id=Y`
- **THEN** retorna las FechaAcademica del tenant filtradas por los parámetros

#### Scenario: Tipo inválido rechazado
- **WHEN** tipo es un valor fuera del enum (Parcial | TP | Coloquio | Recuperatorio)
- **THEN** el sistema retorna HTTP 422

---

### Requirement: Multi-tenancy en todas las operaciones
El sistema SHALL filtrar todas las consultas de Evaluacion, ReservaEvaluacion, ResultadoEvaluacion y FechaAcademica por el tenant_id extraído exclusivamente de la sesión JWT. Un query sin filtro de tenant es un bug.

#### Scenario: Aislamiento entre tenants
- **WHEN** un usuario de tenant_A consulta GET `/api/coloquios`
- **THEN** no recibe ninguna Evaluacion perteneciente a tenant_B

#### Scenario: tenant_id nunca desde el body
- **WHEN** el payload incluye un campo tenant_id explícito
- **THEN** el sistema lo ignora y usa el tenant de la sesión

---

### Requirement: Soft delete de convocatorias
El sistema SHALL implementar soft delete en Evaluacion. Una convocatoria eliminada no aparece en listados activos pero sus reservas y resultados se conservan para auditoría.

#### Scenario: Eliminación de convocatoria
- **WHEN** ADMIN envía DELETE `/api/coloquios/{id}`
- **THEN** el sistema setea deleted_at en Evaluacion y retorna HTTP 200; GET `/api/coloquios` ya no la incluye

#### Scenario: Resultados de convocatoria eliminada siguen accesibles
- **WHEN** se consulta GET `/api/coloquios/{id}/resultados` con id de convocatoria eliminada con permiso admin
- **THEN** retorna HTTP 200 con los resultados históricos

---

### Requirement: Auditoría de acciones de coloquio
El sistema SHALL registrar en AuditLog todas las acciones de creación, modificación, importación de alumnos, y registro de resultados de Evaluacion.

#### Scenario: Acción auditada
- **WHEN** COORDINADOR crea una Evaluacion
- **THEN** se genera un AuditLog con actor, acción, tenant_id, timestamp y entity_id de la evaluación creada
