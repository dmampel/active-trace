## ADDED Requirements

### Requirement: Modelo de padrón versionado

El sistema SHALL persistir el padrón de alumnos de una materia como una `VersionPadron` (contenedor con metadatos de carga) que agrupa una o más `EntradaPadron` (una fila por alumno). Por cada tupla `(tenant_id, materia_id, cohorte_id)` MUST existir como máximo una versión activa simultáneamente. Al activar una nueva versión, la anterior MUST desactivarse en la misma transacción. El campo `email` de `EntradaPadron` MUST almacenarse cifrado con AES-256-GCM. Las versiones anteriores NO se borran — permanecen en el histórico (soft architecture: `activa = false`).

#### Scenario: Crear primera versión de padrón
- **WHEN** se importa el primer padrón para una (materia, cohorte) del tenant
- **THEN** el sistema crea un `VersionPadron` con `activa = true` y N `EntradaPadron` asociadas

#### Scenario: Reemplazar versión activa
- **WHEN** ya existe una `VersionPadron` activa para la misma (materia, cohorte) y se importa un nuevo padrón
- **THEN** la versión anterior queda con `activa = false` y la nueva queda con `activa = true`, en una sola transacción

#### Scenario: Historial preservado
- **WHEN** se listan las versiones de una (materia, cohorte)
- **THEN** el sistema retorna todas las versiones (activa e inactivas) con su metadata de carga

#### Scenario: Email de alumno cifrado en reposo
- **WHEN** se persiste una `EntradaPadron`
- **THEN** el campo `email` está cifrado en la base de datos y solo se expone descifrado a través de la capa de servicio

---

### Requirement: Importación de padrón desde archivo (F1.3)

El sistema SHALL aceptar la importación de padrón de alumnos desde un archivo xlsx o csv a través de `POST /api/v1/padron/{materia_id}/importar`. El actor MUST tener permiso `padron:importar`. El parser MUST detectar automáticamente el formato por extensión o content-type. Las columnas obligatorias son `nombre`, `apellidos` y `email`; columnas adicionales MUST ignorarse sin error. Si el archivo supera 5.000 filas el sistema MUST rechazar la carga con 413.

#### Scenario: Importar xlsx correctamente
- **WHEN** un usuario con permiso `padron:importar` sube un archivo xlsx con columnas `nombre`, `apellidos`, `email` y al menos una fila
- **THEN** el sistema crea una `VersionPadron` activa con las `EntradaPadron` correspondientes y retorna 201 con el resumen (total importado, versión_id)

#### Scenario: Importar csv correctamente
- **WHEN** un usuario con permiso `padron:importar` sube un archivo csv UTF-8 con las columnas obligatorias
- **THEN** el sistema crea una `VersionPadron` activa y retorna 201

#### Scenario: Columnas adicionales ignoradas
- **WHEN** el archivo xlsx contiene columnas extra no reconocidas (`comision`, `legajo`, etc.)
- **THEN** el sistema importa las columnas obligatorias e ignora las extras sin error

#### Scenario: Columna obligatoria faltante
- **WHEN** el archivo no contiene la columna `email`
- **THEN** el sistema retorna 400 Bad Request con mensaje indicando qué columna falta

#### Scenario: Archivo demasiado grande
- **WHEN** el archivo contiene más de 5.000 filas de datos
- **THEN** el sistema retorna 413 Request Entity Too Large sin crear ninguna versión

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `padron:importar` intenta POST al endpoint
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Scope tenant enforced
- **WHEN** el `materia_id` en la URL no pertenece al tenant del JWT
- **THEN** el sistema retorna 404 Not Found (no exponer que existe en otro tenant)

---

### Requirement: Importación de padrón desde Moodle WS (F1.4)

El sistema SHALL permitir obtener el listado de participantes de un curso Moodle a través de `POST /api/v1/padron/{materia_id}/importar-moodle` con `{ "course_id": <int> }`. El cliente Moodle WS MUST usar `httpx` async y las credenciales (`moodle_url`, `moodle_token`) almacenadas cifradas en `tenant_moodle_config`. Si Moodle retorna error, el sistema MUST devolver 503 con un mensaje claro.

#### Scenario: Importar desde Moodle exitosamente
- **WHEN** un usuario con permiso `padron:importar` llama al endpoint con un `course_id` válido y el tenant tiene config Moodle configurada
- **THEN** el sistema obtiene los participantes del WS de Moodle, crea una `VersionPadron` activa y retorna 201

#### Scenario: Config Moodle no configurada para el tenant
- **WHEN** el tenant no tiene `tenant_moodle_config` registrada
- **THEN** el sistema retorna 422 con mensaje "Moodle no configurado para este tenant"

#### Scenario: Moodle WS responde con error de autenticación
- **WHEN** el token Moodle del tenant está expirado o revocado y el WS retorna 403
- **THEN** el sistema retorna 503 con mensaje "Error de autenticación con Moodle. Verificar token." y no crea ninguna versión

#### Scenario: Moodle WS no disponible
- **WHEN** el host de Moodle no responde dentro del timeout
- **THEN** el sistema retorna 503 con mensaje "Moodle no disponible. Intentar más tarde."

---

### Requirement: Config Moodle por tenant (D3)

El sistema SHALL persistir la configuración de conexión a Moodle (`moodle_url`, `moodle_token`) por tenant en la tabla `tenant_moodle_config`. Ambos campos MUST almacenarse cifrados con AES-256-GCM. Solo usuarios con permiso `admin:config` MUST poder crear o actualizar esta configuración vía `PUT /api/v1/admin/moodle-config`.

#### Scenario: Guardar config Moodle
- **WHEN** un usuario con permiso `admin:config` envía PUT con `moodle_url` y `moodle_token`
- **THEN** el sistema persiste ambos valores cifrados y retorna 200

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `admin:config` intenta modificar la config Moodle
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Consulta del padrón activo

El sistema SHALL exponer `GET /api/v1/padron/{materia_id}/activo` para consultar la versión activa de una materia con sus entradas. Requiere permiso `padron:leer`. La respuesta MUST incluir la lista de `EntradaPadron` con `email` descifrado.

#### Scenario: Consultar padrón activo existente
- **WHEN** un usuario con permiso `padron:leer` consulta el endpoint y existe una versión activa
- **THEN** el sistema retorna 200 con la `VersionPadron` y sus `EntradaPadron` (email descifrado)

#### Scenario: Sin padrón activo
- **WHEN** no existe ninguna versión activa para la materia
- **THEN** el sistema retorna 404 con mensaje "Sin padrón activo para esta materia"

#### Scenario: Scope tenant enforced en lectura
- **WHEN** el `materia_id` no pertenece al tenant del JWT
- **THEN** el sistema retorna 404

---

### Requirement: Historial de versiones de padrón

El sistema SHALL exponer `GET /api/v1/padron/{materia_id}/versiones` que retorna todas las `VersionPadron` (activas e inactivas) de la materia. Requiere permiso `padron:leer`.

#### Scenario: Listar historial
- **WHEN** un usuario con permiso `padron:leer` consulta el historial con varias versiones importadas
- **THEN** el sistema retorna la lista ordenada por `cargado_at` descendente con todas las versiones

---

### Requirement: Vaciado de padrón scope-isolated (F1.5 / RN-04)

El sistema SHALL permitir vaciar el padrón de una materia a través de `DELETE /api/v1/padron/{materia_id}/activo`. Esta operación MUST hacer soft-delete de la `VersionPadron` activa importada por el usuario en sesión. NO MUST afectar versiones importadas por otros usuarios. Requiere permiso `padron:importar`.

#### Scenario: Vaciar padrón propio
- **WHEN** un usuario con permiso `padron:importar` llama DELETE y existe una versión activa importada por él mismo
- **THEN** la versión queda con `deleted_at` seteado, retorna 204, y el sistema registra evento de auditoría `PADRON_VACIADO`

#### Scenario: No vaciar padrón de otro usuario
- **WHEN** la versión activa fue importada por otro usuario
- **THEN** el sistema retorna 403 Forbidden (RN-04: scope-isolated)

#### Scenario: Vaciar sin padrón activo
- **WHEN** no existe versión activa para la materia
- **THEN** el sistema retorna 404
