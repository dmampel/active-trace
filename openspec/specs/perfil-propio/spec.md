## ADDED Requirements

### Requirement: Lectura del perfil propio

El sistema SHALL exponer `GET /api/v1/perfil` para que cualquier usuario autenticado lea su propio perfil. La identidad del usuario MUST derivarse exclusivamente del JWT verificado; NUNCA de un parámetro de URL, body o header. La respuesta SHALL devolver los datos del usuario del tenant del autenticado, descifrando la PII propia (`dni`, `cbu`, `alias_cbu`, `cuil`) para mostrarla a su titular. El endpoint requiere el permiso `perfil:editar` (autoservicio) y es fail-closed.

#### Scenario: Usuario lee su propio perfil
- **WHEN** un usuario autenticado solicita `GET /api/v1/perfil`
- **THEN** el sistema retorna 200 con los datos del usuario identificado por el JWT, incluyendo la PII propia descifrada

#### Scenario: Identidad siempre desde el JWT
- **WHEN** una petición a `GET /api/v1/perfil` incluye un `usuario_id` o `legajo` en query, body o header distinto del titular del JWT
- **THEN** el sistema ignora ese dato y resuelve el perfil exclusivamente desde el usuario del JWT verificado

#### Scenario: Petición sin autenticación rechazada
- **WHEN** una petición a `GET /api/v1/perfil` no presenta un JWT válido
- **THEN** el sistema retorna 401 Unauthorized y no expone ningún dato

---

### Requirement: Edición de campos propios del perfil

El sistema SHALL permitir al usuario autenticado editar su propio perfil vía `PATCH /api/v1/perfil`, operando SIEMPRE sobre el usuario del JWT. Los campos editables por el propio usuario son: `nombre`, `apellidos`, `dni`, `sexo`, `cbu`, `alias_cbu`, `banco`, `regional`, `email`, `modalidad_cobro` (factura/liquidación → mapea a `facturador`) y `legajo_profesional`. La PII modificada (`dni`, `cbu`, `alias_cbu`) MUST recifrarse con AES-256 en reposo y NUNCA exponerse en texto plano en logs. El schema de entrada MUST usar `extra='forbid'`. La unicidad `(tenant_id, email)` MUST mantenerse al cambiar el email.

#### Scenario: Editar campos editables del propio perfil
- **WHEN** un usuario autenticado envía `PATCH /api/v1/perfil` con `nombre`, `banco`, `cbu` y `regional` válidos
- **THEN** el sistema actualiza solo esos campos del usuario del JWT, recifra la PII modificada y retorna 200

#### Scenario: PII recifrada en reposo
- **WHEN** un usuario actualiza su `cbu` o `dni` vía `PATCH /api/v1/perfil`
- **THEN** el valor persistido está cifrado (distinto del texto plano) y no aparece en claro en ningún log estructurado

#### Scenario: Cambio de email duplicado en el tenant rechazado
- **WHEN** un usuario intenta cambiar su `email` a uno que ya existe en su mismo tenant
- **THEN** el sistema retorna 409 Conflict y no modifica el perfil

#### Scenario: Campo no declarado rechazado
- **WHEN** un usuario envía `PATCH /api/v1/perfil` con un campo no declarado en el schema
- **THEN** el sistema retorna 422 por `extra='forbid'` y no modifica el perfil

---

### Requirement: CUIL de solo lectura para el usuario

El sistema SHALL tratar el `cuil` (identificador tributario principal) como campo de **solo lectura** en la autogestión del perfil. Un usuario NO puede modificar su propio `cuil` vía `/api/v1/perfil`; ese cambio queda reservado al ABM administrativo (`usuario-management`, permiso `usuarios:gestionar`). El `cuil` SHALL devolverse descifrado en la lectura del perfil propio pero rechazarse como campo editable.

#### Scenario: Intento de modificar el CUIL propio rechazado
- **WHEN** un usuario envía `PATCH /api/v1/perfil` incluyendo el campo `cuil`
- **THEN** el sistema retorna 422 (campo no editable / `extra='forbid'`) y el `cuil` permanece sin cambios

#### Scenario: CUIL visible en lectura pero inmutable
- **WHEN** un usuario lee su perfil vía `GET /api/v1/perfil`
- **THEN** el `cuil` aparece descifrado para su titular, pero ningún PATCH posterior puede alterarlo
