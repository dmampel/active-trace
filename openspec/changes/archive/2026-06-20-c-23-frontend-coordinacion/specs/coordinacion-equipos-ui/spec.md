## ADDED Requirements

### Requirement: Mis equipos — vista del docente autenticado
El sistema SHALL mostrar al usuario autenticado (PROFESOR, TUTOR, NEXO, COORDINADOR) la lista de comisiones y materias en las que está asignado, con rol, carrera, cohorte, vigencia y estado. La vista DEBE ofrecer tres tabs: resumen del equipo, monitoreo de actividad y comunicaciones del equipo.

#### Scenario: Docente ve sus equipos activos
- **WHEN** el usuario navega a `/equipos`
- **THEN** el sistema muestra una tabla con sus asignaciones activas (materia, rol, carrera, cohorte, vigencia, estado)

#### Scenario: Filtros de mis equipos
- **WHEN** el usuario aplica filtro por estado, materia, rol o carrera
- **THEN** la tabla se actualiza mostrando solo las asignaciones que coinciden con el filtro seleccionado

#### Scenario: Tab monitoreo de actividad
- **WHEN** el usuario activa el tab "Actividad"
- **THEN** el sistema carga (lazy) el estado de actividades de los alumnos de esa comisión

---

### Requirement: Consulta y gestión de asignaciones del tenant (coordinador)
El sistema SHALL permitir al COORDINADOR y ADMIN ver todas las asignaciones activas del tenant con filtros por materia, carrera, cohorte, usuario, nombre de docente, rol y relación de reporte.

#### Scenario: Vista de asignaciones del tenant
- **WHEN** un usuario con permiso `equipos:ver` accede a la vista de asignaciones
- **THEN** se muestra la tabla completa de asignaciones del tenant con paginación

#### Scenario: Filtrar asignaciones por materia y rol
- **WHEN** el coordinador selecciona una materia y un rol en los filtros
- **THEN** la tabla muestra únicamente las asignaciones que coinciden con ambos criterios

---

### Requirement: Alta masiva de asignaciones
El sistema SHALL permitir seleccionar múltiples docentes y asignarlos en bloque a una combinación materia × carrera × cohorte × rol con una vigencia definida.

#### Scenario: Asignación masiva exitosa
- **WHEN** el coordinador selecciona N docentes, completa la combinación destino y confirma
- **THEN** el sistema crea N asignaciones y muestra un resumen con el resultado de cada una

#### Scenario: Validación de campos obligatorios en asignación masiva
- **WHEN** el formulario se envía sin materia, cohorte o rol seleccionados
- **THEN** el sistema muestra errores de validación y NO realiza ninguna asignación

---

### Requirement: Clonar equipo docente entre períodos
El sistema SHALL permitir duplicar todas las asignaciones de un equipo origen (materia × carrera × cohorte) hacia un equipo destino, facilitando la migración entre cuatrimestres.

#### Scenario: Clonado exitoso
- **WHEN** el coordinador completa el stepper (origen → destino → confirmación) y confirma
- **THEN** el sistema crea las asignaciones en el destino y muestra el resumen de las filas creadas

#### Scenario: Conflicto al clonar (destino ya tiene asignaciones)
- **WHEN** el backend retorna 409 porque el destino ya tiene asignaciones para esa combinación
- **THEN** el sistema muestra un mensaje descriptivo del conflicto y permite al usuario modificar el destino sin perder la selección de origen

---

### Requirement: Modificar vigencia global del equipo
El sistema SHALL permitir actualizar las fechas de vigencia de todas las asignaciones de un equipo seleccionado en una sola operación.

#### Scenario: Cambio de vigencia exitoso
- **WHEN** el coordinador selecciona un equipo, ingresa nuevas fechas desde/hasta y confirma
- **THEN** el sistema actualiza todas las asignaciones del equipo y muestra confirmación

#### Scenario: Fechas inválidas (hasta < desde)
- **WHEN** el usuario ingresa una fecha "hasta" anterior a "desde"
- **THEN** el formulario muestra un error de validación y bloquea el envío

---

### Requirement: Exportar equipo docente
El sistema SHALL permitir descargar un archivo con el detalle de todas las asignaciones del equipo (docente, rol, materia, carrera, cohorte, vigencia, estado).

#### Scenario: Descarga del export
- **WHEN** el coordinador hace click en "Exportar" en la vista de asignaciones
- **THEN** el navegador descarga un archivo (CSV o Excel) con todas las asignaciones visibles en la tabla actual (aplicando los filtros activos)
