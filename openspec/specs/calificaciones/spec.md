## ADDED Requirements

### Requirement: Modelo de calificación por alumno y actividad

El sistema SHALL persistir la nota de un estudiante en una actividad evaluable como una `Calificacion` que referencia su `EntradaPadron` (`entrada_padron_id`, FK con `ondelete=CASCADE`) y la materia (`materia_id`, UUID indexado, scopeado por tenant). Cada `Calificacion` MUST registrar `actividad` (texto), `nota_numerica` (decimal nullable), `nota_textual` (texto nullable), `origen` (`Importado` | `Manual`) e `importado_at`. El campo `aprobado` NO se persiste como columna: MUST derivarse a partir del umbral vigente. Toda `Calificacion` MUST tener `tenant_id` y soportar soft delete.

#### Scenario: Persistir calificación numérica importada
- **WHEN** se importa una calificación con `nota_numerica` para un alumno del padrón en una actividad
- **THEN** el sistema crea una `Calificacion` con `origen = Importado`, `importado_at` seteado, `entrada_padron_id` y `materia_id` correctos, y `tenant_id` del JWT

#### Scenario: Persistir calificación textual importada
- **WHEN** se importa una calificación con solo `nota_textual` (ej. "Satisfactorio")
- **THEN** el sistema crea una `Calificacion` con `nota_numerica = null` y `nota_textual` poblado

#### Scenario: Soft delete preserva el histórico
- **WHEN** se elimina una calificación
- **THEN** la fila queda con `deleted_at` seteado y nunca se borra físicamente

---

### Requirement: Derivación determinística del estado aprobado

El sistema SHALL derivar el estado `aprobado` de una calificación mediante una función pura de dominio, sin acceso a base de datos. La derivación MUST seguir: (a) si existe `nota_numerica`, `aprobado = nota_numerica >= (umbral_pct / 100) * nota_maxima`; (b) si solo existe `nota_textual`, `aprobado = nota_textual ∈ valores_aprobatorios`; (c) cuando coexisten ambas, la nota numérica MUST tener precedencia; (d) si no existe ninguna nota, `aprobado = false`. El umbral aplicado MUST ser el configurado para la asignación docente, o el valor por defecto del tenant (60%) si no hay configuración.

#### Scenario: Numérica por encima del umbral aprueba
- **WHEN** la nota numérica es 7 sobre una nota máxima de 10 y el umbral es 60%
- **THEN** `aprobado = true` (7 >= 6.0)

#### Scenario: Numérica en el límite exacto del umbral aprueba
- **WHEN** la nota numérica es 6 sobre 10 y el umbral es 60%
- **THEN** `aprobado = true` (6 >= 6.0, comparación inclusiva)

#### Scenario: Numérica por debajo del umbral no aprueba
- **WHEN** la nota numérica es 5 sobre 10 y el umbral es 60%
- **THEN** `aprobado = false`

#### Scenario: Textual dentro del conjunto aprobatorio aprueba
- **WHEN** la nota textual es "Satisfactorio" y `valores_aprobatorios` incluye "Satisfactorio" y "Supera lo esperado"
- **THEN** `aprobado = true`

#### Scenario: Textual fuera del conjunto aprobatorio no aprueba
- **WHEN** la nota textual es "No satisfactorio" y no está en `valores_aprobatorios`
- **THEN** `aprobado = false`

#### Scenario: Precedencia de la nota numérica sobre la textual
- **WHEN** una calificación tiene `nota_numerica = 5` sobre 10 (umbral 60%) y `nota_textual = "Satisfactorio"` (aprobatorio)
- **THEN** `aprobado = false` (la nota numérica tiene precedencia y está por debajo del umbral)

#### Scenario: Sin nota no aprueba
- **WHEN** una calificación no tiene ni `nota_numerica` ni `nota_textual`
- **THEN** `aprobado = false`

---

### Requirement: Importación de calificaciones desde archivo del LMS (F1.1)

El sistema SHALL aceptar la importación de calificaciones desde un archivo de hoja de cálculo exportado del LMS vía un endpoint que requiere permiso `calificaciones:importar`. El parser MUST detectar las columnas de nota numérica como aquellas cuyo encabezado termina en `(Real)` (RN-01); cualquier otra columna NO se procesa como nota numérica. Los valores textuales MUST mapearse según la escala configurada (RN-02). Antes de persistir, el sistema MUST generar una vista previa de las actividades detectadas (con su escala numérica o textual) y los alumnos, sin escribir datos. El sistema MUST persistir y analizar únicamente las actividades que el usuario selecciona.

#### Scenario: Detectar columnas numéricas por sufijo (Real)
- **WHEN** el archivo contiene columnas con encabezados "TP1 (Real)" y "Comentarios"
- **THEN** la vista previa detecta "TP1" como actividad de escala numérica y NO interpreta "Comentarios" como nota numérica

#### Scenario: Detectar columnas textuales
- **WHEN** una columna contiene valores como "Satisfactorio" / "No satisfactorio"
- **THEN** la vista previa detecta esa actividad como de escala textual

#### Scenario: Vista previa no persiste datos
- **WHEN** un usuario con permiso `calificaciones:importar` solicita la vista previa de un archivo
- **THEN** el sistema retorna la lista de actividades y alumnos detectados sin crear ninguna `Calificacion`

#### Scenario: Solo se persisten actividades seleccionadas
- **WHEN** el archivo contiene 3 actividades y el usuario selecciona solo 2 para incluir
- **THEN** el sistema persiste calificaciones únicamente para esas 2 actividades

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `calificaciones:importar` intenta importar
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Scope tenant enforced
- **WHEN** el `materia_id` no pertenece al tenant del JWT
- **THEN** el sistema retorna 404 Not Found (sin revelar existencia en otro tenant)

#### Scenario: Auditoría de importación
- **WHEN** una importación de calificaciones finaliza correctamente
- **THEN** el sistema registra un `AuditLog` con `accion = "CALIFICACIONES_IMPORTAR"`, el `materia_id`, las filas afectadas, IP y user agent, atribuido al actor real del JWT

---

### Requirement: Importación del reporte de finalización (F1.2)

El sistema SHALL aceptar la importación del reporte de finalización de actividades del LMS y cruzarlo con las calificaciones ya importadas para identificar entregas finalizadas por el alumno pero sin calificación registrada (RN-07). La tabla de "posibles trabajos sin corregir" MUST agrupar únicamente actividades de escala textual (RN-08); las actividades de escala numérica MUST excluirse. Requiere permiso `calificaciones:importar`.

#### Scenario: Detectar entrega textual finalizada sin calificación
- **WHEN** el reporte indica que un alumno finalizó una actividad de escala textual y no existe `Calificacion` para esa actividad y alumno
- **THEN** el sistema reporta esa entrega como "posible trabajo sin corregir"

#### Scenario: Actividad numérica excluida del reporte sin corregir
- **WHEN** una actividad finalizada es de escala numérica y no tiene calificación
- **THEN** el sistema NO la incluye en la tabla de "sin corregir" (ausencia de nota numérica = no entregado)

#### Scenario: Entrega ya calificada no figura como sin corregir
- **WHEN** el alumno finalizó una actividad textual y ya tiene una `Calificacion` registrada para ella
- **THEN** esa entrega NO figura como "sin corregir"

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `calificaciones:importar` intenta importar el reporte de finalización
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Configuración de umbral de aprobación por asignación docente (F2.1)

El sistema SHALL permitir a un docente configurar el umbral de aprobación de una materia como una `UmbralMateria` anclada a su `asignacion_id` (FK), con `umbral_pct` (entero, defecto 60) y `valores_aprobatorios` (lista de valores textuales aprobatorios). El umbral MUST aplicar solo a los datos del docente de esa asignación; configurar el umbral de un docente NO MUST afectar los datos ni el umbral de otro docente en la misma materia (RN-03, RN-04 análogo). Si no existe `UmbralMateria`, el sistema MUST usar el valor por defecto del tenant (60%). Requiere permiso `calificaciones:importar`. Toda `UmbralMateria` MUST tener `tenant_id`.

#### Scenario: Configurar umbral propio
- **WHEN** un docente con permiso `calificaciones:importar` define `umbral_pct = 70` para su asignación en una materia
- **THEN** el sistema persiste un `UmbralMateria` con `umbral_pct = 70` para esa asignación y tenant

#### Scenario: Umbral por defecto cuando no hay configuración
- **WHEN** se deriva `aprobado` para una calificación y no existe `UmbralMateria` para la asignación
- **THEN** el sistema aplica el umbral por defecto del tenant (60%)

#### Scenario: Aislamiento de scope entre docentes
- **WHEN** el docente A cambia su `umbral_pct` a 80 en una materia donde el docente B también tiene asignación con umbral 60
- **THEN** el umbral del docente B permanece en 60 y sus calificaciones derivan `aprobado` con su propio umbral

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `calificaciones:importar` intenta configurar el umbral
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Scope tenant enforced en configuración
- **WHEN** la `asignacion` o `materia_id` no pertenecen al tenant del JWT
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Permisos RBAC de calificaciones

El sistema SHALL definir los permisos `calificaciones:importar` (asignado a PROFESOR y COORDINADOR) y `calificaciones:leer` (asignado a PROFESOR, TUTOR, COORDINADOR y ADMIN), sembrados en la migración del módulo. Todo endpoint del módulo de calificaciones MUST declarar `require_permission(...)` y ser fail-closed: sin permiso explícito, retorna 403. La identidad, roles y tenant del actor MUST derivarse exclusivamente de la sesión JWT, nunca de la URL, body o header.

#### Scenario: Permiso de importación concedido a PROFESOR
- **WHEN** un usuario con rol PROFESOR y permiso `calificaciones:importar` importa calificaciones de su materia
- **THEN** el sistema procesa la importación

#### Scenario: Permiso de lectura concedido a TUTOR
- **WHEN** un usuario con rol TUTOR y permiso `calificaciones:leer` consulta calificaciones
- **THEN** el sistema retorna los datos sin error de autorización

#### Scenario: Identidad derivada del JWT, no de la petición
- **WHEN** una petición incluye un `tenant_id` o `usuario_id` en el body o la URL distinto al de la sesión
- **THEN** el sistema ignora esos valores y opera con la identidad y tenant del JWT verificado
