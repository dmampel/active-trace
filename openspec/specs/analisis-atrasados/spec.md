## ADDED Requirements

### Requirement: Computar alumnos atrasados
El sistema SHALL computar el conjunto de alumnos atrasados para una materia dado el umbral configurado (RN-06). Un alumno es atrasado si tiene al menos una actividad faltante o con nota inferior al umbral. El cómputo es on-the-fly sobre los datos de `calificacion` + `umbral_materia` + `entrada_padron`. El acceso requiere el permiso `atrasados:ver`.

#### Scenario: Alumno con nota numérica menor al umbral aparece como atrasado
- **WHEN** un alumno tiene `nota_numerica` < `umbral_pct`% de la nota máxima en alguna actividad seleccionada
- **THEN** el sistema lo incluye en la lista de atrasados con las actividades problemáticas detalladas

#### Scenario: Alumno con actividad faltante aparece como atrasado
- **WHEN** un alumno del padrón no tiene ninguna calificación registrada para una actividad seleccionada
- **THEN** el sistema lo incluye en la lista de atrasados marcando esa actividad como "faltante"

#### Scenario: Alumno con nota textual aprobatoria no aparece como atrasado
- **WHEN** un alumno tiene `nota_textual` que pertenece al conjunto `valores_aprobatorios` en todas las actividades
- **THEN** el sistema NO lo incluye en la lista de atrasados

#### Scenario: PROFESOR solo ve sus alumnos
- **WHEN** un usuario con rol PROFESOR llama al endpoint de atrasados con una `materia_id`
- **THEN** el sistema solo retorna alumnos cuya `entrada_padron` está vinculada a la `asignacion_id` activa del PROFESOR en esa materia

#### Scenario: COORDINADOR ve todos los alumnos del tenant
- **WHEN** un usuario con rol COORDINADOR llama al endpoint de atrasados con una `materia_id`
- **THEN** el sistema retorna atrasados de todos los alumnos del tenant en esa materia, sin restricción por asignacion_id

---

### Requirement: Ranking de actividades aprobadas
El sistema SHALL exponer un ranking de alumnos ordenado descendentemente por cantidad de actividades aprobadas (RN-09). El ranking MUST excluir alumnos sin ninguna actividad aprobada. Requiere `atrasados:ver`.

#### Scenario: Alumno con aprobadas aparece en el ranking
- **WHEN** un alumno tiene al menos una calificación con `aprobado = true`
- **THEN** aparece en el ranking con el conteo total de actividades aprobadas

#### Scenario: Alumno sin aprobadas no aparece en el ranking
- **WHEN** un alumno tiene todas sus calificaciones con `aprobado = false` o no tiene calificaciones
- **THEN** NO aparece en el ranking

#### Scenario: Ranking ordenado descendentemente
- **WHEN** el endpoint de ranking es invocado
- **THEN** la lista de alumnos aparece ordenada de mayor a menor cantidad de actividades aprobadas

---

### Requirement: Reportes rápidos por materia
El sistema SHALL computar métricas consolidadas de la materia: total de alumnos, total de alumnos atrasados, porcentaje de aprobación por actividad, y cantidad de actividades seleccionadas. Requiere `atrasados:ver`.

#### Scenario: Reporte devuelve métricas correctas cuando hay datos
- **WHEN** la materia tiene calificaciones importadas y al menos un alumno en el padrón
- **THEN** el sistema retorna: `total_alumnos`, `atrasados`, `pct_aprobacion_por_actividad`, `actividades_count`

#### Scenario: Reporte cuando no hay datos
- **WHEN** la materia no tiene calificaciones importadas o el padrón está vacío
- **THEN** el sistema retorna métricas en cero sin error (estado informativo vacío)

---

### Requirement: Notas finales agrupadas
El sistema SHALL calcular una nota final por alumno sumando (o promediando según configuración) las calificaciones de las actividades seleccionadas por el docente. El resultado es exportable como CSV. Requiere `atrasados:ver`.

#### Scenario: Nota final calculada correctamente para alumno con todas las actividades
- **WHEN** todas las actividades seleccionadas tienen calificación para el alumno
- **THEN** el sistema computa la nota final según la función de agregación configurada y la incluye en la respuesta

#### Scenario: Actividad faltante penaliza la nota final
- **WHEN** un alumno no tiene calificación registrada para una actividad seleccionada
- **THEN** esa actividad cuenta como 0 en el cómputo de la nota final

---

### Requirement: Detectar y exportar TPs sin corregir
El sistema SHALL aceptar un archivo de finalización del LMS y cruzarlo con las calificaciones textuales existentes para identificar actividades finalizadas por el alumno pero sin nota registrada (RN-07, RN-08). MUST aplicar solo a actividades de escala textual. El resultado es exportable como CSV.

#### Scenario: Actividad textual finalizada sin nota se detecta como pendiente
- **WHEN** el alumno tiene estado "finalizada" en el reporte de finalización para una actividad textual Y no tiene calificación textual ni numérica para esa actividad
- **THEN** el sistema incluye ese par (alumno, actividad) en la lista de "posibles TPs sin corregir"

#### Scenario: Actividad numérica no aparece en el listado de TPs sin corregir
- **WHEN** una actividad es de escala numérica (RN-08)
- **THEN** el sistema la excluye de la detección de TPs sin corregir, independientemente del estado de finalización

#### Scenario: Actividad textual ya calificada no aparece como pendiente
- **WHEN** el alumno tiene una calificación textual registrada para esa actividad
- **THEN** el sistema NO la incluye en la lista de pendientes

#### Scenario: Export CSV de TPs sin corregir
- **WHEN** el endpoint de exportación es invocado tras la detección
- **THEN** el sistema responde con un archivo CSV descargable con columnas: apellido, nombre, email (descifrado), actividad, estado_finalizacion

---

### Requirement: Monitor general de alumnos (coordinación y admin)
El sistema SHALL proveer un endpoint de monitor transversal que permita a COORDINADOR y ADMIN consultar el estado de actividades de todos los alumnos del tenant con filtros (RN-06, F2.7). Requiere `atrasados:ver`.

#### Scenario: Filtro por materia acota resultados al tenant
- **WHEN** el COORDINADOR filtra por `materia_id`
- **THEN** solo aparecen alumnos de esa materia dentro del tenant

#### Scenario: Filtro por comisión (regional)
- **WHEN** el COORDINADOR aplica filtro por `comision`
- **THEN** solo aparecen alumnos cuya `entrada_padron.comision` coincide

#### Scenario: Filtro libre por nombre/email
- **WHEN** el COORDINADOR ingresa un término de búsqueda libre
- **THEN** el sistema filtra alumnos cuyo nombre o email (descifrado) contiene el término

#### Scenario: Acceso al monitor genera registro de auditoría
- **WHEN** el monitor general es consultado
- **THEN** el sistema genera un evento de auditoría con código `ANALISIS_ATRASADOS_VER`

---

### Requirement: Monitor de seguimiento tutor/profesor
El sistema SHALL proveer un monitor restringido al scope del usuario autenticado (TUTOR o PROFESOR) que muestra el estado de actividades de sus propios alumnos con filtros adicionales (F2.8). Requiere `atrasados:ver`.

#### Scenario: TUTOR solo ve sus alumnos
- **WHEN** el TUTOR llama al monitor de seguimiento
- **THEN** el sistema solo retorna alumnos de las asignaciones activas del TUTOR

#### Scenario: Filtro por mínimo de actividades cumplidas
- **WHEN** el TUTOR aplica un filtro `min_actividades_cumplidas = N`
- **THEN** solo aparecen alumnos con N o más actividades aprobadas

---

### Requirement: Monitor coordinación con filtro de fechas
El sistema SHALL extender el monitor de seguimiento con un filtro de rango de fechas para COORDINADOR y ADMIN (F2.9). Requiere `atrasados:ver`.

#### Scenario: Filtro de rango de fechas acota el período de análisis
- **WHEN** el COORDINADOR aplica `fecha_desde` y `fecha_hasta`
- **THEN** solo se incluyen calificaciones cuyo `importado_at` cae dentro del rango

#### Scenario: Sin rango de fechas el monitor muestra todos los datos disponibles
- **WHEN** el COORDINADOR no aplica filtro de fechas
- **THEN** el monitor incluye todas las calificaciones sin restricción temporal
