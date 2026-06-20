# coordinacion-academica-ui Specification

## Purpose
TBD - created by archiving change c-23-frontend-coordinacion. Update Purpose after archive.
## Requirements
### Requirement: Monitor general de actividades (coordinación/admin)
El sistema SHALL proveer al COORDINADOR y ADMIN una vista transversal de todos los alumnos del tenant con su estado de actividades. Los filtros disponibles son: materia, regional, comisión, búsqueda libre por alumno, estado de actividad y criterio de clasificación.

#### Scenario: Acceso al monitor general
- **WHEN** el usuario con permiso `atrasados:ver` accede a `/coordinacion/monitores`
- **THEN** se muestra la tabla de alumnos del tenant con columnas de estado de actividades

#### Scenario: Filtrar por materia y estado
- **WHEN** el coordinador selecciona una materia y el filtro "Atrasado"
- **THEN** la tabla muestra solo los alumnos de esa materia en estado Atrasado

#### Scenario: Exportar resultados del monitor
- **WHEN** el usuario hace click en "Exportar"
- **THEN** el navegador descarga un archivo con los alumnos visibles en la tabla (con los filtros activos aplicados)

---

### Requirement: Monitor de seguimiento con rango de fechas (coordinación)
El sistema SHALL extender el monitor de seguimiento (F2.8) con un filtro adicional de rango de fechas para acotar el período de análisis, disponible para COORDINADOR y ADMIN.

#### Scenario: Filtrar por rango de fechas
- **WHEN** el coordinador accede a `/coordinacion/monitores/seguimiento` y selecciona un rango de fechas
- **THEN** el monitor muestra solo las actividades dentro del rango indicado

#### Scenario: Fechas no obligatorias
- **WHEN** el coordinador deja el rango de fechas vacío
- **THEN** el monitor funciona igual que el monitor estándar de seguimiento sin límite de fechas

---

### Requirement: Vista de administración de encuentros (coordinador)
El sistema SHALL mostrar al COORDINADOR y ADMIN todos los encuentros del tenant (más allá del docente que los creó), con posibilidad de supervisión y monitoreo global.

#### Scenario: Lista de todos los encuentros del tenant
- **WHEN** el coordinador accede a `/coordinacion/encuentros`
- **THEN** se muestra la lista de todos los encuentros del tenant con materia, docente, fecha, estado y enlace de grabación

#### Scenario: Filtrar encuentros por materia y estado
- **WHEN** el coordinador filtra por materia "Programación 4" y estado "Realizado"
- **THEN** la lista muestra solo los encuentros realizados de esa materia

---

### Requirement: Registro y consulta de guardias (coordinador)
El sistema SHALL mostrar al COORDINADOR y ADMIN el registro de guardias cubiertas por tutores, con filtros y exportación.

#### Scenario: Ver registro de guardias
- **WHEN** el coordinador accede a la sección guardias dentro de `/coordinacion/encuentros`
- **THEN** se muestra la tabla de guardias con tutor, materia, carrera/cohorte, día, horario, estado y comentarios

#### Scenario: Exportar guardias
- **WHEN** el coordinador hace click en "Exportar guardias"
- **THEN** se descarga un archivo con las guardias filtradas actualmente

---

### Requirement: Panel de métricas de coloquios
El sistema SHALL mostrar al COORDINADOR y ADMIN las métricas operativas de coloquios: total de alumnos cargados, instancias activas, reservas activas y notas registradas.

#### Scenario: Ver métricas al acceder a coloquios
- **WHEN** el coordinador accede a `/coordinacion/coloquios`
- **THEN** se muestran los KPIs de cabecera (alumnos cargados, instancias activas, reservas, notas) y la lista de convocatorias

---

### Requirement: Gestión de convocatorias de coloquio
El sistema SHALL permitir crear convocatorias con materia, nombre de instancia, días disponibles y cupos; listar convocatorias activas con métricas; e importar el padrón de alumnos habilitados.

#### Scenario: Crear convocatoria
- **WHEN** el coordinador completa el formulario de nueva convocatoria y confirma
- **THEN** la convocatoria aparece en la lista con sus días y cupos configurados

#### Scenario: Importar padrón de candidatos
- **WHEN** el coordinador sube un archivo con alumnos habilitados para una convocatoria
- **THEN** el sistema importa el padrón y actualiza el contador de convocados en la fila de la convocatoria

#### Scenario: Ver reservas activas de una convocatoria
- **WHEN** el coordinador accede al detalle de una convocatoria
- **THEN** se muestra la agenda de reservas activas con alumno, día y cupo reservado

---

### Requirement: Registro académico consolidado de coloquios
El sistema SHALL mostrar el registro de notas finales de coloquio por convocatoria, permitiendo la consulta del resultado académico de cada alumno.

#### Scenario: Ver notas finales de una convocatoria
- **WHEN** el coordinador accede al tab "Registro académico" de una convocatoria
- **THEN** se muestra la lista de alumnos con su nota final de coloquio y estado (Aprobado / Desaprobado / Ausente)

#### Scenario: Convocatoria sin notas cargadas
- **WHEN** la convocatoria no tiene ningún resultado registrado
- **THEN** la vista muestra un estado vacío descriptivo sin errores

