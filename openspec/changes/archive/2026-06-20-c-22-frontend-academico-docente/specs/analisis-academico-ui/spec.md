## ADDED Requirements

### Requirement: Página de análisis con tabs
El sistema SHALL proveer una página en `/comision/:comisionId/analisis` con las pestañas: "Atrasados", "Ranking", "Reportes", "Notas finales". Cuando no hay datos importados para la comisión, SHALL mostrar un estado vacío con llamado a la acción de importar.

#### Scenario: Sin datos importados muestra estado vacío con CTA
- **WHEN** el usuario navega a `/comision/:comisionId/analisis` y no hay calificaciones importadas
- **THEN** se muestra el mensaje "Aún no hay datos para esta comisión" y un botón que navega al wizard de importación

#### Scenario: Con datos importados las tabs son navegables
- **WHEN** hay calificaciones importadas para la comisión
- **THEN** las cuatro pestañas están activas y la pestaña "Atrasados" está seleccionada por defecto

### Requirement: Configuración de umbral de aprobación
El sistema SHALL mostrar el umbral de aprobación activo de la comisión en la página de análisis y permitir editarlo via un control inline o modal, accesible solo con permiso `calificaciones:importar`.

#### Scenario: Umbral activo se muestra en la cabecera de análisis
- **WHEN** la página de análisis carga con datos importados
- **THEN** se muestra "Umbral de aprobación: X%" en la cabecera

#### Scenario: Editar umbral actualiza el cálculo de atrasados
- **WHEN** el usuario modifica el umbral y guarda
- **THEN** el backend persiste el nuevo umbral, la cache de atrasados se invalida y la tabla se recalcula con el nuevo criterio

### Requirement: Tabla de alumnos atrasados
El sistema SHALL mostrar en la pestaña "Atrasados" una tabla de alumnos con columnas: nombre, correo, actividades faltantes y nota promedio. La tabla SHALL soportar ordenamiento por columna y filtrado por texto libre sobre nombre/correo.

#### Scenario: Tabla muestra alumnos debajo del umbral
- **WHEN** la pestaña "Atrasados" está activa
- **THEN** solo aparecen alumnos con actividades faltantes o nota menor al umbral configurado

#### Scenario: Filtro por nombre/correo acota la tabla
- **WHEN** el usuario escribe en el campo de búsqueda
- **THEN** la tabla muestra solo los alumnos cuyo nombre o correo contiene el texto ingresado (sin distinguir mayúsculas)

#### Scenario: Tabla vacía cuando todos están al día
- **WHEN** ningún alumno está atrasado según el umbral
- **THEN** se muestra el mensaje "¡Todos los alumnos están al día!" dentro de la pestaña

### Requirement: Ranking de actividades aprobadas
El sistema SHALL mostrar en la pestaña "Ranking" una tabla ordenada descendentemente por cantidad de actividades aprobadas. Solo se incluyen alumnos con al menos una actividad aprobada.

#### Scenario: Ranking ordena correctamente por actividades aprobadas
- **WHEN** la pestaña "Ranking" está activa
- **THEN** la tabla muestra alumnos ordenados de mayor a menor por cantidad de actividades aprobadas; alumnos con cero aprobadas no aparecen

#### Scenario: Cambio de orden por columna reordena la tabla
- **WHEN** el usuario hace clic en el encabezado de una columna
- **THEN** la tabla se reordena por esa columna de forma ascendente/descendente alternando en cada clic

### Requirement: Reportes rápidos de la comisión
El sistema SHALL mostrar en la pestaña "Reportes" un panel con métricas clave: total de alumnos, porcentaje de alumnos al día, cantidad de actividades incluidas en el análisis y promedio general de la comisión.

#### Scenario: Panel de métricas se renderiza con los datos del backend
- **WHEN** la pestaña "Reportes" está activa y hay datos importados
- **THEN** las cuatro métricas se muestran como tarjetas con su valor numérico y etiqueta

#### Scenario: Métricas se actualizan tras cambio de umbral
- **WHEN** el usuario cambia el umbral de aprobación y guarda
- **THEN** las métricas del panel se recalculan y reflejan el nuevo umbral

### Requirement: Notas finales agrupadas
El sistema SHALL mostrar en la pestaña "Notas finales" una tabla con nota final calculada por alumno. La tabla SHALL ser exportable a CSV.

#### Scenario: Tabla de notas finales muestra un registro por alumno
- **WHEN** la pestaña "Notas finales" está activa
- **THEN** cada alumno aparece una sola vez con su nota final calculada por el backend

#### Scenario: Exportar notas a CSV descarga el archivo
- **WHEN** el usuario hace clic en "Exportar CSV"
- **THEN** el navegador inicia la descarga de un archivo `.csv` con los datos de la tabla

### Requirement: Exportar entregas sin corregir
El sistema SHALL proveer un botón "Exportar" en la tabla de TPs sin corregir. El botón SHALL estar deshabilitado si la tabla está vacía.

#### Scenario: Exportar TPs sin corregir descarga CSV
- **WHEN** hay filas en la tabla de TPs sin corregir y el usuario hace clic en "Exportar"
- **THEN** el navegador inicia la descarga de un `.csv` con las columnas alumno, actividad y estado

#### Scenario: Botón exportar deshabilitado sin datos
- **WHEN** la tabla de TPs sin corregir está vacía
- **THEN** el botón "Exportar" aparece deshabilitado

### Requirement: Monitor de seguimiento del docente/tutor (F2.8)
El sistema SHALL proveer una página en `/comision/:comisionId/monitor` accesible para roles TUTOR y PROFESOR con filtros por alumno (nombre/correo), comisión, regional, actividad y mínimo de actividad cumplida. La lista SHALL mostrar solo los alumnos asignados al usuario autenticado.

#### Scenario: Lista muestra solo alumnos asignados al usuario
- **WHEN** el PROFESOR navega al monitor
- **THEN** la tabla muestra únicamente los alumnos de sus comisiones asignadas (identidad desde sesión, no desde URL)

#### Scenario: Filtro por mínimo de actividad cumplida acota resultados
- **WHEN** el usuario ingresa un valor en el filtro "Mínimo de actividades cumplidas"
- **THEN** la tabla muestra solo los alumnos con al menos ese número de actividades cumplidas

#### Scenario: Aplicar múltiples filtros simultáneos
- **WHEN** el usuario activa más de un filtro a la vez
- **THEN** la tabla muestra la intersección de todos los criterios activos

#### Scenario: Limpiar filtros restaura la lista completa
- **WHEN** el usuario hace clic en "Limpiar filtros"
- **THEN** todos los filtros se resetean y la tabla muestra todos los alumnos asignados sin restricción
